"""
  My take on the manual alarm control panel
"""
import datetime
import logging
import enum
import re
import voluptuous as vol
from operator import attrgetter

from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING, STATE_ALARM_TRIGGERED, CONF_PLATFORM, CONF_NAME,
    CONF_CODE, CONF_PENDING_TIME, CONF_TRIGGER_TIME, CONF_DISARM_AFTER_TRIGGER,
    EVENT_STATE_CHANGED, EVENT_TIME_CHANGED, STATE_ON)
from homeassistant.util.dt import utcnow as now
from homeassistant.helpers.event import async_track_point_in_time
import homeassistant.components.alarm_control_panel as alarm
import homeassistant.components.switch as switch
import homeassistant.helpers.config_validation as cv

CONF_HEADSUP   = 'headsup'
CONF_IMMEDIATE = 'immediate'
CONF_DELAYED   = 'delayed'
CONF_NOTATHOME = 'notathome'
CONF_ALARM     = 'alarm'
CONF_WARNING   = 'warning'

# Add a new state for the time after an delayed sensor and an actual alarm
STATE_ALARM_WARNING = 'warning'

class Events(enum.Enum):
    ImmediateTrip = 1
    DelayedTrip   = 2
    ArmHome       = 3
    ArmAway       = 4
    Timeout       = 5
    Disarm        = 6
    Trigger       = 7
    
PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM):  'bwalarm',
    vol.Required(CONF_NAME):      cv.string,
    vol.Required(CONF_PENDING_TIME): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Required(CONF_TRIGGER_TIME): vol.All(vol.Coerce(int), vol.Range(min=1)),
    vol.Required(CONF_ALARM):     cv.entity_id,  # switch/group to turn on when alarming
    vol.Required(CONF_WARNING):   cv.entity_id,  # switch/group to turn on when warning
    vol.Optional(CONF_HEADSUP):   cv.entity_ids, # things to show as a headsup, not alarm on
    vol.Optional(CONF_IMMEDIATE): cv.entity_ids, # things that cause an immediate alarm
    vol.Optional(CONF_DELAYED):   cv.entity_ids, # things that allow a delay before alarm
    vol.Optional(CONF_NOTATHOME): cv.entity_ids  # things that we ignore when at home
})

_LOGGER = logging.getLogger(__name__)

def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    alarm = BWAlarm(hass, config)
    hass.bus.async_listen(EVENT_STATE_CHANGED, alarm.state_change_listener)
    hass.bus.async_listen(EVENT_TIME_CHANGED, alarm.time_change_listener)
    yield from async_add_devices([alarm])


class BWAlarm(alarm.AlarmControlPanel):

    def __init__(self, hass, config):
        """ Initalize the alarm system """
        self._hass         = hass
        self._name         = config[CONF_NAME]
        self._immediate    = set(config.get(CONF_IMMEDIATE, []))
        self._delayed      = set(config.get(CONF_DELAYED, []))
        self._notathome    = set(config.get(CONF_NOTATHOME, []))
        self._allinputs    = self._immediate | self._delayed | self._notathome
        self._allsensors   = self._allinputs | set(config.get(CONF_HEADSUP, []))
        self._alarm        = config[CONF_ALARM]
        self._warning      = config[CONF_WARNING]
        self._pending_time = datetime.timedelta(seconds=config[CONF_PENDING_TIME])
        self._trigger_time = datetime.timedelta(seconds=config[CONF_TRIGGER_TIME])

        self._lasttrigger  = ""
        self._state        = STATE_ALARM_DISARMED
        self._returnto     = STATE_ALARM_DISARMED
        self._timeoutat    = None
        self.clearsignals()

    ### Alarm properties

    @property
    def should_poll(self) -> bool: return False
    @property
    def name(self) -> str:         return self._name
    @property
    def changed_by(self) -> str:   return self._lasttrigger
    @property
    def state(self) -> str:        return self._state
    @property
    def device_state_attributes(self):
        return {
            'immediate':  sorted(list(self.immediate)),
            'delayed':    sorted(list(self.delayed)),
            'ignored':    sorted(list(self.ignored)),
            'allsensors': sorted(list(self._allsensors)),
            'changedby':  self.changed_by
        }


    ### Actions from the outside world that affect us, turn into enum events for internal processing

    def time_change_listener(self, eventignored):
        """ I just treat the time events as a periodic check, its simpler then (re-/un-)registration """
        if self._timeoutat is not None:
            if now() > self._timeoutat:
                self._timeoutat = None
                self.process_event(Events.Timeout)

    def state_change_listener(self, event):
        """ Something changed, we only care about things turning on at this point """
        new = event.data.get('new_state', None)
        if new is None or new.state != STATE_ON:
            return
        eid = event.data['entity_id']
        if eid in self.immediate:
            self._lasttrigger = eid
            self.process_event(Events.ImmediateTrip)
        elif eid in self.delayed:
            self._lasttrigger = eid
            self.process_event(Events.DelayedTrip)

    def alarm_disarm(self, code=None):
        self.process_event(Events.Disarm)

    def alarm_arm_home(self, code=None):
        self.process_event(Events.ArmHome)

    def alarm_arm_away(self, code=None):
        self.process_event(Events.ArmAway)

    def alarm_trigger(self, code=None):
        self.process_event(Events.Trigger)


    ### Internal processing

    def noton(self, eid):
        """ For filtering out sensors already tripped """
        return not self._hass.states.is_state(eid, STATE_ON)

    def setsignals(self, athome):
        """ Figure out what to sense and how """
        self.immediate = set(filter(self.noton, self._immediate))
        self.delayed = set(filter(self.noton, self._delayed))
        if athome:
            self.immediate -= self._notathome
            self.delayed -= self._notathome
        self.ignored = self._allinputs - (self.immediate | self.delayed)

    def clearsignals(self):
        """ Clear all our signals, we aren't listening anymore """
        self.immediate = set()
        self.delayed = set()
        self.ignored = self._allinputs.copy()

    def process_event(self, event):
        """ 
           This is the core logic function.
           The possible states and things that can change our state are:
                 Actions:  isensor dsensor timeout arm_home arm_away disarm trigger
           Current State: 
             disarmed         X       X       X      armh     pend     *     trig
             pending(T1)      X       X      arma     X        X      dis    trig
             armed(h/a)      trig    warn     X       X        X      dis    trig
             warning(T1)      X       X      trig     X        X      dis    trig
             triggered(T2)    X       X      last     X        X      dis     *

           As the only non-timed states are disarmed, armed_home and armed_away,
           they are the only ones we can return to after an alarm.
        """
        old = self._state

        # Update state if applicable
        if event == Events.Disarm:
            self._state = STATE_ALARM_DISARMED
        elif event == Events.Trigger:
            self._state = STATE_ALARM_TRIGGERED 
        elif old == STATE_ALARM_DISARMED:
            if   event == Events.ArmHome:       self._state = STATE_ALARM_ARMED_HOME
            elif event == Events.ArmAway:       self._state = STATE_ALARM_PENDING
        elif old == STATE_ALARM_PENDING:
            if   event == Events.Timeout:       self._state = STATE_ALARM_ARMED_AWAY
        elif old == STATE_ALARM_ARMED_HOME or \
             old == STATE_ALARM_ARMED_AWAY:
            if   event == Events.ImmediateTrip: self._state = STATE_ALARM_TRIGGERED
            elif event == Events.DelayedTrip:   self._state = STATE_ALARM_WARNING
        elif old == STATE_ALARM_WARNING:
            if   event == Events.Timeout:       self._state = STATE_ALARM_TRIGGERED
        elif old == STATE_ALARM_TRIGGERED:
            if   event == Events.Timeout:       self._state = self._returnto

        new = self._state
        if old != new: 
            _LOGGER.debug("Alarm changing from {} to {}".format(old, new))
            # Things to do on entering state
            if new == STATE_ALARM_WARNING:
                _LOGGER.debug("Turning on warning")
                switch.turn_on(self._hass, self._warning)
                self._timeoutat = now() + self._pending_time
            elif new == STATE_ALARM_TRIGGERED:
                _LOGGER.debug("Turning on alarm")
                switch.turn_on(self._hass, self._alarm)
                self._timeoutat = now() + self._trigger_time
            elif new == STATE_ALARM_PENDING:
                _LOGGER.debug("Pending user leaving house")
                switch.turn_on(self._hass, self._warning)
                self._timeoutat = now() + self._pending_time
                self._returnto = STATE_ALARM_ARMED_AWAY
                self.setsignals(False)
            elif new == STATE_ALARM_ARMED_HOME:
                self._returnto = new
                self.setsignals(True)
            elif new == STATE_ALARM_DISARMED:
                self._returnto = new
                self.clearsignals()

            # Things to do on leaving state
            if old == STATE_ALARM_WARNING or old == STATE_ALARM_PENDING:
                _LOGGER.debug("Turning off warning")
                switch.turn_off(self._hass, self._warning)
            elif old == STATE_ALARM_TRIGGERED:
                _LOGGER.debug("Turning off alarm")
                switch.turn_off(self._hass, self._alarm)

            # Let HA know that something changed
            self.update_ha_state()



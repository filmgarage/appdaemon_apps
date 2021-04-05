import appdaemon.plugins.hass.hassapi as hass
import voluptuous as vol
import datetime # required for time to str conversion
import requests # required for http GET

# Config constants
CONF_CLASS = "class"
CONF_MODULE = "module"
CONF_CREDENTIALS = "credentials"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_IPS = "ip_addresses"
CONF_START_OFFSET = "start_time_offset"
CONF_END_OFFSET = "end_time_offset"

CONST_IP_SEPARATOR = "."
CONST_HTTP_ENDPOINT = "/settings/night_mode"
CONST_HTTP_PARAMETER_SEPARATOR = "&"

# Specific parameter validation functions
def checkifIP(value):
  octets = value.split(".")
  if len(octets) == 4:
    for octet in octets:
      try:
        octet_int = int(octet)
        if not 0 <= octet_int <= 255:
          raise ValueError
      except:
        raise ValueError
      finally:
        return value
  else:
    raise ValueError

#Voluptuous Schema
APP_SCHEMA = vol.Schema(
  {
    vol.Required(CONF_MODULE): str,
    vol.Required(CONF_CLASS): str,
    vol.Required(CONF_IPS): [checkifIP],
    vol.Optional(CONF_CREDENTIALS): vol.Schema({
      vol.Required(CONF_USERNAME): str,
      vol.Required(CONF_PASSWORD): str,
    }),
    vol.Optional(CONF_START_OFFSET): vol.All(str, vol.Length(min=5,max=8)),
    vol.Optional(CONF_END_OFFSET): vol.All(str, vol.Length(min=5,max=8)),
  }
)

class ShellyAutoNightMode(hass.Hass):

  def initialize(self):
    
    #Check app parameters with Voluptuous
    try:
      APP_SCHEMA(self.args)
    except vol.Invalid as err:
      self.error(f"Invalid format: {err}", level='ERROR')
      return

    # get parameters
    self.shelly_credentials = self.args.get(CONF_CREDENTIALS, None)
    self.ip_addresses = self.args.get(CONF_IPS)
    self.start_time_offset = self.args.get(CONF_START_OFFSET, "00:00")
    self.end_time_offset = self.args.get(CONF_END_OFFSET, "00:00")

    # initialize parameters
    self.http_parameters = {}

    # determine start/end time HTTP parameters
    self.http_parameters["start_time"] = self.parse_time("sunset + " + self.start_time_offset + ":00").strftime("%H:%M")
    self.http_parameters["end_time"] = self.parse_time("sunrise - " + self.end_time_offset + ":00").strftime("%H:%M")
    
    self.start_time = self.parse_time("sunset + " + self.start_time_offset + ":00").strftime("%H:%M")
    self.end_time = self.parse_time("sunrise - " + self.end_time_offset + ":00").strftime("%H:%M")

    # run daily at 12PM
    self.run_daily(self.main, "12:00:00")

  def update_nightmode(self, kwargs):

    for ip in self.ip_addresses:
      #get http credentials
      if self.shelly_credentials is None:
        http_credentials = ""
      else:
        username = self.shelly_credentials[CONF_USERNAME]
        password = self.shelly_credentials[CONF_PASSWORD]
        http_credentials = username + ":" + password + "@"
      
      #get endpoint parameters
      if len(self.http_parameters) > 0:
        url_parameters = CONST_HTTP_PARAMETER_SEPARATOR.join([f'{key}={value}' for (key, value) in self.http_parameters.items()])
        http_url = "http://" + http_credentials + ip \
                  + CONST_HTTP_ENDPOINT + "?"\
                  + url_parameters
        requests.get(http_url)
    
    self.log("Shelly Dimmer Night Mode times have been updated.\n" + \
              "Start time is: " + self.http_parameters["start_time"] + ".\n" + \
              "End time is: " + self.http_parameters["end_time"] + ".")


import appdaemon.plugins.hass.hassapi as hass
import voluptuous as vol
import requests # required for http GET

# Constants
CONF_CLASS = "class"
CONF_MODULE = "module"
CONF_CREDENTIALS = "credentials"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_IPS = "current_ip_address_list"
CONF_NETWORK_INFO = "new_network_information"
CONF_SSID = "ssid"
CONF_STATIC_IPV4_DETAILS = "static_ipv4"
CONF_GATEWAY = "gateway"
CONF_NETMASK = "netmask"
CONF_DNS = "dns"
CONF_HOST_ID_START = "host_id_start"
CONF_HOST_ID_EXCEPTIONS = "host_id_exceptions"

CONST_IP_SEPARATOR = "."
CONST_HTTP_ENDPOINT = "/settings/sta"
CONST_HTTP_PARAMETER_SEPARATOR = "&"

# Specific argument validation functions
def checkifIP(value):
  octets = value.split(CONST_IP_SEPARATOR)
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
    vol.Required(CONF_NETWORK_INFO): vol.Schema({
      vol.Optional(CONF_CREDENTIALS): vol.Schema({
        vol.Required(CONF_SSID): str,
        vol.Required(CONF_PASSWORD): str,
      }),
      vol.Optional(CONF_STATIC_IPV4_DETAILS): vol.Schema({
        vol.Required(CONF_GATEWAY): checkifIP,
        vol.Required(CONF_NETMASK): checkifIP,
        vol.Optional(CONF_DNS): checkifIP,
        vol.Optional(CONF_HOST_ID_START): int,
        vol.Optional(CONF_HOST_ID_EXCEPTIONS): [int],
      }),
    }),
  }
)

class ShellyUpdateWifiCredentials(hass.Hass):

  def initialize(self):
    
    #Check app parameters with Voluptuous
    try:
      APP_SCHEMA(self.args)
    except vol.Invalid as err:
      self.error(f"Invalid format: {err}", level='ERROR')
      return

    # get parameters
    self.shelly_credentials = self.args.get(CONF_CREDENTIALS, None)
    self.current_ip_address_list = self.args.get(CONF_IPS)
    self.gateway = self.args[CONF_NETWORK_INFO][CONF_STATIC_IPV4_DETAILS][CONF_GATEWAY]
    self.host_id = self.args.get(CONF_NETWORK_INFO).get(CONF_STATIC_IPV4_DETAILS).get(CONF_HOST_ID_START,2)
    self.host_id_exceptions = sorted(self.args[CONF_NETWORK_INFO][CONF_STATIC_IPV4_DETAILS][CONF_HOST_ID_EXCEPTIONS])

    # run once - now
    self.main()

  def update_wifi(self):

    # Get string for Shelly credentials. Blank string if non-existant.
    if self.shelly_credentials is None:
      url_credentials = ""
    else:
      username = self.shelly_credentials[CONF_USERNAME]
      password = self.shelly_credentials[CONF_PASSWORD]
      url_credentials = username + ":" + password + "@"

    # initialize parameters
    self.http_parameters = {}

    #Get parameters for new network details
    if CONF_CREDENTIALS in self.args[CONF_NETWORK_INFO]:
      self.http_parameters["ssid"] = self.args[CONF_NETWORK_INFO][CONF_CREDENTIALS][CONF_SSID]
      self.http_parameters["key"] = self.args[CONF_NETWORK_INFO][CONF_CREDENTIALS][CONF_PASSWORD]
    
    if CONF_STATIC_IPV4_DETAILS in self.args[CONF_NETWORK_INFO]:
      self.http_parameters["ipv4_method"] = "static"
      self.http_parameters["gw"] = self.gateway
      self.http_parameters["netmask"] = self.args[CONF_NETWORK_INFO][CONF_STATIC_IPV4_DETAILS][CONF_NETMASK]
    else:
      self.http_parameters["ipv4_method"] = "dhcp"

    if CONF_DNS in self.args[CONF_NETWORK_INFO][CONF_STATIC_IPV4_DETAILS]:
      self.http_parameters["dns"] = self.args[CONF_NETWORK_INFO][CONF_STATIC_IPV4_DETAILS][CONF_DNS]
    
    self.network_id = self.get_network_id(self.gateway)                 

    #Serialise start of URL
    for ip in self.current_ip_address_list:

      # increment new host IP if in exceptions
      if self.host_id_exceptions is not None:
        while self.host_id in self.host_id_exceptions:
          self.host_id += 1

      # Get new IP address and serialise HTTP URL
      new_ip = self.network_id + CONST_IP_SEPARATOR + str(self.host_id)
      self.http_parameters["ip"] = new_ip
      if len(self.http_parameters) > 0:
        url_parameters = CONST_HTTP_PARAMETER_SEPARATOR.join([f'{key}={value}' for (key, value) in self.http_parameters.items()])
        http_url = "http://" + url_credentials + ip + CONST_HTTP_ENDPOINT \
                  + "?" + url_parameters
        
        self.log(http_url)
        # requests.get(http_url)

      self.host_id += 1
    
    self.log("Shelly WiFi details updated.")

  def get_network_id(self, gateway, network_class="C"):

    if network_class == "C":
      network_id_octet_count = 3

    gateway_octets = gateway.split(CONST_IP_SEPARATOR)
    network_id = CONST_IP_SEPARATOR.join(gateway_octets[0:(network_id_octet_count)])
    return network_id
import requests
from ansible.module_utils.basic import AnsibleModule, env_fallback, return_values

requests.packages.urllib3.disable_warnings()


class Netscaler(object):
    """
    This is the Base Class for Netscaler modules. All methods common across several Netscaler Classes should be defined
    here and inherited by the sub-class.
    """

    def __init__(self, host, user, passw, use_ssl=True, verify=False, api_endpoint="", **kwargs):
        """
        :param host: Type str.
                     The IP or resolvable hostname of the Netscaler.
        :param user: Type str.
                     The username used to authenticate with the Netscaler.
        :param passw: Type str.
                      The password associated with the user account.
        :param use_ssl: Type bool.
                        The default is True, which uses HTTPS instead of HTTP.
        :param verify: Type bool.
                       The default is False, which does not verify the certificate against the list of trusted
                       certificates.
        :param api_endpoint: Type str.
                             The API endpoint used for a particular configuration section.
        :param headers: Type dict.
                        The headers to include in HTTP requests.
        :param kwargs: Type dict. Currently supports port.
        :param port: Type str.
                     Passing the port parameter will override the default HTTP(S) port when making requests.
        """
        self.host = host
        self.user = user
        self.passw = passw
        self.verify = verify
        self.api_endpoint = api_endpoint
        self.headers = {"Content-Type": "application/json"}
        if "port" not in kwargs:
            self.port = ""
        else:
            self.port = ":{}".format(kwargs["port"])

        if use_ssl:
            self.url = "https://{lb}{port}/nitro/v1/config/".format(lb=self.host, port=self.port)
            self.stat_url = "https://{lb}{port}/nitro/v1/stat/".format(lb=self.host, port=self.port)
        else:
            self.url = "http://{lb}{port}/nitro/v1/config/".format(lb=self.host, port=self.port)
            self.stat_url = "http://{lb}{port}/nitro/v1/stat/".format(lb=self.host, port=self.port)

    def change_name(self, existing_name, proposed_name):
        """
        The purpose of this method is to change the name of a server object.
        :param existing_name: Type str.
                              The name of the server object to be renamed.
        :param proposed_name: Type str.
                              The new name of the server object.
        :return: The response from the request to delete the object.
        """
        url = self.url + self.api_endpoint + "?action=rename"
        body = {self.api_endpoint: {"name": existing_name, "newname":proposed_name}}
        response = self.session.post(url, json=body, headers=self.headers, verify=self.verify)

        return response

    def change_state(self, object_name, state):
        """
        The purpose of this method is to change the state of an object from either disabled to enabled, or enabled to
        disabled. This method assumes the object is referenced by "name." This is the most common reference key, but not
        universal; where the Nitro API uses another key, an overriding method must be created in the sub-class.
        :param object_name: Type str.
                            The name of the object to be deleted.
        :param state: Type str.
                      The state the object should be in after execution. Valid values are "enable" or "disable"
        :return: The response from the request to delete the object.
        """
        url = self.url + self.api_endpoint + "?action={}".format(state)
        body = {self.api_endpoint: {"name": object_name}}
        response = self.session.post(url, json=body, headers=self.headers, verify=self.verify)

        return response

    def config_delete(self, module, object_name):
        """
        This method is used to handle the logic for Ansible modules when the "state" is set to "absent." The
        delete_config method is used to delete the object from the Netscaler.
        :param module: The AnsibleModule instance started by the task.
        :param object_name: Type str.
                            The name of the object to be deleted.
        :return: The config dict corresponding to the config returned by the Ansible module.
        """
        config = []

        if not module.check_mode:
            config_status = self.delete_config(object_name)
            if config_status.ok:
                config.append({"method": "delete", "url": config_status.url, "body": {}})
            else:
                logout = self.logout()
                module.fail_json(msg="Unable to Delete Object", netscaler_response=config_status.json(), logout=logout.ok)
        else:
            url = self.url + self.api_endpoint + "/" + object_name
            config.append({"method": "delete", "url": url, "body": {}})

        return config

    def config_new(self, module, new_config):
        """
        This method is used to handle the logic for Ansible modules when the "state" is set to "present" and the
        proposed config is a new object. The post_config method is used to post the object's configuration to the
        Netscaler.
        :param module: The AnsibleModule instance started by the task.
        :param new_config: Type dict.
                           The configuration to send to the Nitro API.
        :return: A list with config dictionary corresponding to the config returned by the Ansible module.
        """
        config = []

        if not module.check_mode:
            config_status = self.post_config(new_config)
            if config_status.ok:
                config.append({"method": "post", "url": config_status.url, "body": new_config})
            else:
                logout = self.logout()
                module.fail_json(msg="Unable to Add New Object", netscaler_response=config_status.json(), logout=logout.ok)
        else:
            config.append({"method": "post", "url": self.url + self.api_endpoint, "body": new_config})

        return config

    def config_rename(self, module, existing_name, proposed_name):
        """
        This method is used to handle the logic for Ansible modules when the "state" is set to "present" and the
        proposed IP Address matches the IP Address of another Server in the same Traffic Domain. The change_name
        method is used to post the configuration to the Netscaler.
        :param module: The AnsibleModule instance started by the task.
        :param existing_name: Type str.
                              The current name of the Server object to be changed.
        :param proposed_name: Type str.
                              The name the Server object should be changed to.
        :return: A list with config dictionary corresponding to the config returned by the Ansible module.
        """
        config = []

        rename_config = {"name": existing_name, "newname": proposed_name}

        if not module.check_mode:
            config_status = self.change_name(existing_name, proposed_name)
            if config_status.ok:
                config.append({"method": "post", "url": config_status.url, "body": rename_config})
            else:
                logout = self.logout()
                module.fail_json(msg="Unable to Rename Object", netscaler_response=config_status.json(), logout=logout.ok)
        else:
            config.append({"method": "post", "url": self.url + self.api_endpoint + "?action=rename", "body": rename_config})

        return config

    def config_update(self, module, update_config):
        """
        This method is used to handle the logic for Ansible modules when the "state" is set to "present" and the
        proposed config modifies an existing object. If the object's state needs to be updated, the "state" key,value is
        popped from the update_config in order to prevent it from being included in a config update when there are
        updates besides state change. The change_state method is then used to modify the object's state. After the
        object's state matches the proposed state, a check is done to see if the update_config has any keys other than
        the "name" key (len > 1). If there are more updates to make, the put_config method is used to push those to the
        Netscaler. Note that this method uses the common "name" key to input to the change_state method; if the API
        Endpoint uses a different key, then an overriding method must be created in the sub-class.
        :param module: The AnsibleModule instance started by the task.
        :param update_config: Type dict.
                              The configuration to send to the Nitro API.
        :return: The list of config dictionaries corresponding to the config returned by the Ansible module.
        """
        config = []

        if "state" in update_config:
            config_state = update_config.pop("state")[:-1].lower()
            if not module.check_mode:
                config_status = self.change_state(update_config["name"], config_state)
                if config_status.ok:
                    config.append({"method": "post", "url": config_status.url, "body": {"name": update_config["name"]}})
                else:
                    logout = self.logout()
                    module.fail_json(msg="Unable to Change Object's State", netscaler_response=config_status.json(), logout=logout.ok)
            else:
                url = self.url + self.api_endpoint + "?action={}".format(config_state)
                config.append({"method": "post", "url": url, "body": {"name": update_config["name"]}})

        if len(update_config) > 1:
            if not module.check_mode:
                config_status = self.put_update(update_config)
                if config_status.ok:
                    config.append({"method": "put", "url": self.url, "body": update_config})
                else:
                    logout = self.logout()
                    module.fail_json(msg="Unable to Update Config", netscaler_response=config_status.json(), logout=logout.ok)
            else:
                config.append({"method": "put", "url": self.url, "body": update_config})

        return config

    def delete_config(self, object_name):
        """
        The purpose of this method is to remove an object from the Netscaler's configuration. Currently no checks are
        made to verify if the object is bound to another item.
        :param object_name: Type str.
                            The name of the object to be deleted.
        :return: The response from the request to delete the object.
        """
        url = self.url + self.api_endpoint + "/" + object_name
        response = self.session.delete(url, headers=self.headers, verify=self.verify)

        return response

    def get_all(self, api_endpoint):
        """
        The purpose of this method is to retrieve every object's configuration for the API endpoint.
        :param api_endpoint: Type str.
                             The API endpoint to use for data collection.
        :return: A list of configuration dictionaries returned by they Nitro API. An empty list means that their are
                 currently no objects configured, or the request was unsuccessful.
        """
        response = self.session.get(self.url + api_endpoint, headers=self.headers, verify=self.verify)

        return response.json().get(api_endpoint, [])

    def get_all_attrs(self, api_endpoint, attrs_list):
        """
        The purpose of this method is to retrieve every object's configuration for the API endpoint, but the
        collected data is restricted to the attributes in the attrs_list argument.
        :param api_endpoint: Type str.
                             The API endpoint to use for data collection.
        :param attrs_list: Type list,tuple
                           The list of attributes used to limit the scope of returned config data.
        :return: A list of configuration dictionaries returned by they Nitro API. An empty list means that their are
                 currently no objects configured, or the request was unsuccessful.
        """
        attrs = "?attrs=" + ",".join(attrs_list)
        url = self.url + api_endpoint + attrs

        response = self.session.get(url, headers=self.headers, verify=self.verify)

        return response.json().get(api_endpoint, [])

    def get_config(self, defaults="false"):
        """
        This method retrieves the running configuration from the Netscaler.
        :param defaults: Type str.
                         The default setting will retrieve configurations that do not have their default setting.
                         Setting this to "true" will retrieve the full configuration including defaults.
        :return: The configuration of the Netscaler as a str. An empty str is returned if the request is unsuccessful.
        """
        url = self.url + "nsrunningconfig?args=withdefaults:{}".format(defaults)
        response = self.session.get(url, headers=self.headers, verify=self.verify)

        return response.json().get("nsrunningconfig", {"response": ""})["response"]

    @staticmethod
    def get_diff(proposed, existing):
        """
        This method is used to compare the proposed config with what currently exists on the Netscaler. Note that thi
        method uses the most common key used by Nitro, "name." Where Nitro uses a different key, the corresponding class
        must have an overriding method.
        :param proposed: Type dict.
                         A dictionary corresponding to the proposed configuration item. The dictionary must have a
                         "name" key.
        :param existing: Type dict.
                         A dictionary corresponding to the existing configuration for the object. This can be retrieved
                         using the get_existing_attrs method.
        :return: A tuple indicating whether the config is a new object, will update an existing object, or make no
                 changes, and a dict that corresponds to the body of a config request using the Nitro API.
        """
        diff = dict(set(proposed.items()).difference(existing.items()))

        if diff == proposed:
            return "new", diff
        elif diff:
            diff["name"] = proposed["name"]
            return "update", diff
        else:
            return "none", {}

    def get_existing_attrs(self, object_name, attrs):
        """
        This method is used to get a subset of a particular object's configuration for the given API Endpoint
        (configuration section). The configuration will be scoped to the list of values in attrs.
        :param object_name: Type str.
                            The name of the object.
        :param attrs: Type list.
                      The list of attributes to retrieve from the configuration.
        :return: A dictionary of the object's configuration. If the object doesn't exist or the request fails, then an
        empty dict is returned. Unexpected empty lists are likely caused by a mistyped API endpoint or an expired
        session.
        """
        attributes = ",".join(attrs)
        url = self.url + self.api_endpoint + "/" + object_name + "?attrs=" + attributes
        response = self.session.get(url, headers=self.headers, verify=self.verify)

        return response.json().get(self.api_endpoint, [{}])[0]

    def get_hardware(self):
        """
        This method is used to retrieve basic hardware information about the Netscaler.
        :return: A dictionary of hardware information. An empty dictionary is returned if the request is unsuccessful.
        """
        response = self.session.get(self.url + "nshardware", headers=self.headers, verify=self.verify)

        return response.json().get("nshardware", {})

    def get_hostname(self):
        """
        This method is used to retrieve the hostname of the connected Netscaler
        :return: A dictionary of the hostname configuration. An empty dictionary is returned if the API request failed.
        """
        response = self.session.get(self.url + "nshostname", headers=self.headers, verify=self.verify)

        return response.json().get("nshostname", [{}])[0]

    def get_interfaces(self):
        """
        This method is used to get the interfaces and their stats from the Netscaler.
        :return: A list of interface dictionaries containing configuration and statistical info. An empty list is
                 returned if the request is unsuccessful.
        """
        response = self.session.get(self.url + "interface", headers=self.headers, verify=self.verify)

        return response.json().get("Interface", [])

    def get_csvserver_stats(self):
        """
        This method is used to get the csvserver statistical info for all vservers on the Netscaler.
        :return: A list of dictionaries for all statistical data for the csvservers. An empty dictionary is returned if
                 the request is unsuccessful.
        """
        response = self.session.get(self.stat_url + "csvserver", headers=self.headers, verify=self.verify)

        return response.json().get("csvserver", [])

    def get_nsconfig(self):
        """
        This method is used to get the nsconfig data from the Netscaler.
        :return: A dictionary of the nsconfig data. An empty dictionary is returned if the request is unsuccessful.
        """
        response = self.session.get(self.url + "nsconfig", headers=self.headers, verify=self.verify)

        return response.json().get("nsconfig", {})

    def get_state(self, object_name):
        """
        This method is used to retrieve the current state of the object. The possibilities are enabled or disabled.
        :param object_name: Type str.
                            The name of the object.
        :return: A str representing the current state of the object. An empty string is returned when the object does
                 not exist.
        """
        url = self.url + self.api_endpoint + object_name + "attrs=state"
        response = self.session.get(url, headers=self.headers, verify=self.verify)

        return response.json().get(self.api_endpoint, [{"state": ""}])[0]["state"]

    def get_system(self):
        """
        This method is used to retrieve the system or environment statistics from the Netscaler.
        :return: A dictionary of the systems statistics (fans, memory, cpu, temp, disk space). An empty dictionary is
        returned if the request is unsuccessful.
        """
        response = self.session.get(self.stat_url + "system", headers=self.headers, verify=self.verify)

        return response.json().get("system", {})

    def login(self):
        """
        The login method is used to establish a session with the Netscaler. All necessary parameters need to be
        established at class instantiation. The requests Session class is used to maintain session consistency for all
        subsequent requests. The Session class automatically stores the cookie returned from the login request, and
        passes the cookie on all requests after a successful login. This is important when using partitions since the
        Netscaler API (Nitro) does not support modifying partitions using basic auth. Note that using partitions still
        requires calling the switch_partition function; these are separated so as to separate the failure domains.
        :return: The response from the login request. A successful login also sets the instance session.
        """
        url = self.url + "login"
        body = {"login": {"username": self.user, "password": self.passw}}
        session = requests.Session()
        login = session.post(url, json=body, headers=self.headers, verify=self.verify)

        if login.ok:
            self.session = session

        return login

    def logout(self):
        """
        The logout method is used to close the established connection with the Netscaler device.
        :return: The response from the logout request.
        """
        url = self.url + "logout"
        body = {"logout": {}}
        logout = self.session.post(url, json=body, headers=self.headers, verify=self.verify)

        return logout

    def post_config(self, new_config):
        """
        This method is used to submit a configuration request to the Netscaler using the Nitro API.
        :param new_config: Type dict:
                           The new configuration item to be sent to the Netscaler. It is expected that you use the
                           get_diff method to generate the new_config data.
        :return: The response from the request to add the configuration.
        """
        url = self.url + self.api_endpoint
        body = {self.api_endpoint: new_config}
        response = self.session.post(url, json=body, headers=self.headers, verify=self.verify)

        return response

    def put_update(self, update_config):
        """
        This method is used to update the configuration of an existing item on the Netscaler.
        :param update_config: Type dict:
                              The configuration item to be sent to the Netscaler in order to update existing object. It
                              is expected that you use the get_diff method to generate the update_config data.
        :return: The response from the request to add the configuration.
        """
        url = self.url + self.api_endpoint
        body = {self.api_endpoint: update_config}
        response = self.session.put(url, json=body, headers=self.headers, verify=self.verify)

        return response

    def save_config(self):
        """
        This method is used to save the config of the Netscaler.
        :return: The response from the request to save the config.
        """
        url = self.url + "nsconfig?action=save"
        response = self.session.post(url, json={"nsconfig": {}}, headers=self.headers, verify=self.verify)

        return response

    def switch_partition(self, partition):
        """
        This method will switch from the default partition to the specified partition.
        :param partition: Type str.
                          The partition to interact with for all subsequent requests.
        :return: The response from the request to switch partitions.
        """
        url = self.url + "nspartition?action=Switch"
        body = {"nspartition": {"partitionname": partition}}
        switch = self.session.post(url, json=body, headers=self.headers, verify=self.verify)

        return switch

    @staticmethod
    def validate_ip(ip_address):
        """
        This method is used to validate that an IPv4 Address has 4 octets and that each octet is an int from 0 to 255.
        Note, "0.0.0.0" is a valid IP.
        :param ip_address: Type str.
                           An IPv4 address.
        :return: A valid IP returns True; otherwise, False.
        """
        octet_split = ip_address.split(".")
        if len(octet_split) != 4:
            return False

        for octet in octet_split:
            try:
                int_octet = int(octet)
            except ValueError:
                return False

            if 0 > int_octet or 255 < int_octet:
                return False

        return True


class CSVServer(Netscaler):
    """
    This is the class used for interacting with the "csvserver" API endpoint. In addition to csvserver specific methods,
    the api endpoint default value is set to "csvserver."
    """

    def __init__(self, host, user, passw, secure=True, verify=False, api_endpoint="csvserver", **kwargs):
        super(CSVServer, self).__init__(host, user, passw, secure, verify, api_endpoint, **kwargs)

    def add_csvserver_lbvserver_binding(self, module, new_config):

        config = []

        if not module.check_mode:
            config_status = self.bind_lbvserver(new_config)
            if config_status.ok:
                config.append({"method": "post", "url": config_status.url, "body": new_config})
            else:
                logout = self.logout()
                module.fail_json(msg="Unable to Bind lbvserver", netscaler_response=config_status.json(), logout=logout.ok)
        else:
            config.append({"method": "post", "url": self.url + self.api_endpoint + "_lbvserver_binding",
                           "body": new_config})

        return config

    def bind_lbvserver(self, new_config):

        url = self.url + self.api_endpoint + "_lbvserver_binding"
        body = {self.api_endpoint + "_lbvserver_binding": new_config}
        response = self.session.post(url, json=body, headers=self.headers, verify=self.verify)

        return response

    def get_all(self):

        response = self.session.get(self.url + self.api_endpoint, headers=self.headers, verify=self.verify)

        return response.json().get(self.api_endpoint, [])

    def get_all_attrs(self, attrs_list):

        attrs = "?attrs=" + ",".join(attrs_list)
        url = self.url + self.api_endpoint + attrs

        response = self.session.get(url, headers=self.headers, verify=self.verify)

        return response.json().get(self.api_endpoint, [])

    def get_csvserver_lbvserver_binding(self, object_name):

        attrs_list = object_name.keys()
        attrs = "?attrs=" + ",".join(attrs_list)
        url = self.url + "csvserver_lbvserver_binding/" + object_name["name"] + attrs
        response = self.session.get(url, headers=self.headers, verify=self.verify)

        return response.json().get("csvserver_lbvserver_binding", [])

    def remove_csvserver_lbvserver_binding(self, module, new_config):

        config = []

        if not module.check_mode:
            config_status = self.unbind_lbvserver(new_config)
            if config_status.ok:
                config.append({"method": "delete", "url": config_status.url, "body": {}})
            else:
                logout = self.logout()
                module.fail_json(msg="Unable to Remove lbvserver", netscaler_response=config_status.json(), logout=logout.ok)
        else:
            args_list = new_config.items()
            args = "?args="
            for k, v in args_list:
                if k != args_list[-1][0]:
                    args += k + ":" + str(v) + ","
                else:
                    args += k + ":" + str(v)

            config.append({"method": "delete", "url": self.url + "csvserver_lbvserver_binding" + args, "body": {}})

        return config

    def unbind_lbvserver(self, binding_config):

        args_list = binding_config.items()
        args = "?args="
        for k, v in args_list:
            if k != args_list[-1][0]:
                args += k + ":" + str(v) + ","
            else:
                args += k + ":" + str(v)

        url = self.url + "csvserver_lbvserver_binding" + args
        response = self.session.delete(url, headers=self.headers, verify=self.verify)

        return response



def main():
    argument_spec = dict(
        host=dict(required=False, type="str"),
        port=dict(required=False, type="int"),
        username=dict(fallback=(env_fallback, ["ANSIBLE_NET_USERNAME"])),
        password=dict(fallback=(env_fallback, ["ANSIBLE_NET_PASSWORD"]), no_log=True),
        use_ssl=dict(required=False, type="bool"),
        validate_certs=dict(required=False, type="bool"),
        provider=dict(required=False, type="dict"),
        state=dict(choices=["absent", "present"], type="str"),
        partition=dict(required=False, type="str"),
        csvserver_name=dict(required=False, type="str"),
        lbvserver_name=dict(required=False, type="str")

    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    provider = module.params["provider"] or {}

    no_log = ["password"]
    for param in no_log:
        if provider.get(param):
            module.no_log_values.update(return_values(provider[param]))

    # allow local params to override provider
    for param, pvalue in provider.items():
        if module.params.get(param) is None:
            module.params[param] = pvalue

    # module specific args that can be represented as both str or int are normalized to Netscaler's representation for diff comparison in case provider is used
    host = module.params["host"]
    partition = module.params["partition"]
    password = module.params["password"]
    port = module.params["port"]
    state = module.params["state"]
    if not state:
        state = "present"
    use_ssl = module.params["use_ssl"]
    if use_ssl is None:
        use_ssl = True
    username = module.params["username"]
    validate_certs = module.params["validate_certs"]
    if validate_certs is None:
        validate_certs = False
    lbvserver_name = module.params["lbvserver_name"]
    if lbvserver_name:
        lbvserver_name = lbvserver_name.upper()

    args = dict(
        name=module.params["csvserver_name"],
        lbvserver=module.params["lbvserver_name"]
    )

    # check for required values, this allows all values to be passed in provider
    argument_check = dict(host=host, csvserver_name=args["name"],lbvserver_name=args["lbvserver"])
    for key, val in argument_check.items():
        if not val:
            module.fail_json(msg="The {} parameter is required".format(key))

    proposed = dict((k, v) for k, v in args.items() if isinstance(v, bool) or v)

    #proposed = dict(
    #    name=module.params["csvserver_name"],
    #    lbvserver=module.params["lbvserver_name"]
    #)

    kwargs = dict()
    if port:
        kwargs["port"] = port

    session = CSVServer(host, username, password, use_ssl, validate_certs, **kwargs)
    session_login = session.login()
    if not session_login.ok:
        module.fail_json(msg="Unable to Login", netscaler_response=session_login.json())

    if partition:
        session_switch = session.switch_partition(partition)
        if not session_switch.ok:
            session_logout = session.logout()
            module.fail_json(msg="Unable to Switch Partitions", netscaler_response=session_switch.json(), logout=session_logout.ok)

    #existing_attrs = args.keys()
    #existing = session.get_existing_attrs(proposed["name"], existing_attrs)
    all_existing = session.get_csvserver_lbvserver_binding(proposed)

    if state == "present":
        results = change_config(session, module, proposed,all_existing)
    else:
        results = delete_csvserver_lbvserver_binding(session, module, proposed, all_existing)

    session_logout = session.logout()
    results["logout"] = session_logout.ok

    return module.exit_json(**results)


def change_config(session, module, proposed, all_existing):

    changed = False
    config = []

    if proposed not in all_existing:
        changed = True
        config = session.add_csvserver_lbvserver_binding(module, proposed)
        existing = {}
    else:
        existing = proposed

    return dict(changed=changed, config=config, existing=existing,all_existing=all_existing)

def delete_csvserver_lbvserver_binding(session, module, proposed, all_existing):

    changed = False
    config = []

    if proposed in all_existing:
        changed = True
        config = session.remove_csvserver_lbvserver_binding(module, proposed)
        existing = proposed
    else:
        existing = {}

    return dict(all_existing=all_existing, changed=changed, config=config, existing=existing)


if __name__ == "__main__":
    main()

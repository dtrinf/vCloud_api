#!/usr/bin/env python
import requests
from pprint import pprint
import xml.etree.ElementTree as ET
import time




class VM:
	'VM Class'

	def __init__(self, headers, href, name, vapp, vapp_url, network, network_url, storage_profile, vdc_url):
		self.href = href
		self.name = name
		self.vapp = vapp
		self.vapp_url = vapp_url
		self.network = network
		self.network_url = network_url
		self.storage_profile = storage_profile
		self.vdc_url = vdc_url
		self.headers = headers

	def __repr__(self):
		print( "name "+ self.name )
		print( "href "+	self.href )
		print( "vapp "+	self.vapp )
		print( "vapp_url "+	self.vapp_url )
		print( "network "+	self.network )
		print( "network_url "+	self.network_url )
		print( "storage_profile "+	self.storage_profile )
		print( "vdc_url "+	self.vdc_url )
		return ""

	def isTemplate(self):
		response = requests.get(self.href, headers = self.headers)


	def xml(self):
		response = requests.get(self.href, headers = self.headers)
		pprint(response.text)

	def getCpuUsage(self):
		""" Get the CPU percentage usage, -1 if poweroff, 0 if error"""
		response = requests.get(self.href+"/metrics/current", headers = self.headers)
		if response.status_code != 200:
			return -1
		root = ET.fromstring(response.text)
		for child in root.findall("{http://www.vmware.com/vcloud/v1.5}Metric"):
			try:
				if child.attrib['name'] == "cpu.usage.average":
					return child.attrib['value']
			except:
				return 0

	def getMemUsage(self):
		""" Get the CPU percentage usage, -1 if poweroff, 0 if error"""
		response = requests.get(self.href+"/metrics/current", headers = self.headers)
		if response.status_code != 200:
			return -1
		root = ET.fromstring(response.text)
		for child in root.findall("{http://www.vmware.com/vcloud/v1.5}Metric"):
			try:
				if child.attrib['name'] == "mem.usage.average":
					return child.attrib['value']
			except:
				return 0

	def getPowerStatus(self):
		""" Get VM Power Status """

		# 4 - Encendido
		# 8 - Parcialmente apagado (powerOff)/ Apagado del todo (Undeploy)

		response = requests.get(self.href, headers = self.headers)
		root = ET.fromstring(response.text)

		return root.get("status")

	def getIP(self):
		""" Return VM IP """

		response = requests.get(self.href+'/networkConnectionSection/', headers = self.headers)
		root = ET.fromstring(response.text)

		if response.status_code != 200:
			return -1
		for child in root.findall('.//{http://www.vmware.com/vcloud/v1.5}IpAddress'):
			try:
				if child.tag == "{http://www.vmware.com/vcloud/v1.5}IpAddress":
					return child.text
			except:
				return 0

	def powerOff(self):
		""" Turns Off VM """
		#Power Off the VM
		response = requests.post(self.href+"/power/action/powerOff", headers = self.headers)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0

	def powerOffUndeploy(self):
		""" Turns Off VM """
		#Power Off the VM
		#Undeploy VM
		self.headers["Content-Type"] = "application/vnd.vmware.vcloud.undeployVAppParams+xml"

		xml_data = """<UndeployVAppParams xmlns="http://www.vmware.com/vcloud/v1.5">
			<UndeployPowerAction>powerOff</UndeployPowerAction>
		</UndeployVAppParams>"""

		response = requests.post(self.href+"/action/undeploy", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0

	def powerOn(self):
		""" Turns On VM """
		#Power On the VM
		response = requests.post(self.href+"/power/action/powerOn", headers = self.headers)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			print("error al arrancar")
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)
			#response = requests.post(self.href+"/action/undeploy", headers = self.headers)
			return 0

	def deleteVm(self):
		""" Delete VM """

		xml_data = """<?xml version="1.0" encoding="UTF-8"?>
					<RecomposeVAppParams
					   name="%s"
					   xmlns="http://www.vmware.com/vcloud/v1.5"
					   xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
					   <AllEULAsAccepted>true</AllEULAsAccepted>
					   <DeleteItem href="%s"/>
					</RecomposeVAppParams>"""%(self.vapp, self.href)

		self.headers["Content-Type"] = "application/vnd.vmware.vcloud.recomposeVAppParams+xml"
		response = requests.post(self.vapp_url+"/action/recomposeVApp", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0


	def cloneVm(self, newName, vorg, vapp = "", network = "", lock = "True"):
		""" Clone VM: if we clone from a template, all params are needed """

		if vapp == "":
			vapp = self.vapp

		if network == "":
			network = self.network

		currentVapp = vorg.getVapp(vapp)

		xml_data = """<?xml version="1.0" encoding="UTF-8"?>
					<RecomposeVAppParams
					   name="%s"
					   xmlns="http://www.vmware.com/vcloud/v1.5"
					   xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
						<SourcedItem sourceDelete="false">
							<Source href="%s"/>
							<VmGeneralParams>
								<!-- Nombre del server en vCloud -->
								<Name>%s</Name>
								<Description>Elastic Node</Description>
								<NeedsCustomization>true</NeedsCustomization>
							</VmGeneralParams>
							<InstantiationParams>
								<!-- Nombre interno del server -->
								<GuestCustomizationSection xmlns="http://www.vmware.com/vcloud/v1.5"
															xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
															type="application/vnd.vmware.vcloud.guestCustomizationSection+xml"
															ovf:required="false">
									<ovf:Info />
									<Enabled>true</Enabled>
									<ComputerName>%s</ComputerName>
								</GuestCustomizationSection>
								<NetworkConnectionSection xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
															type="application/vnd.vmware.vcloud.networkConnectionSection+xml"
															href="%s/networkConnectionSection/"
															ovf:required="false">
									<ovf:Info/>
									<PrimaryNetworkConnectionIndex>0</PrimaryNetworkConnectionIndex>
									<NetworkConnection network="%s">
										<NetworkConnectionIndex>0</NetworkConnectionIndex>
										<IsConnected>true</IsConnected>
										<IpAddressAllocationMode>POOL</IpAddressAllocationMode>
									</NetworkConnection>
								</NetworkConnectionSection>
							</InstantiationParams>
						</SourcedItem>
						<AllEULAsAccepted>true</AllEULAsAccepted>
					</RecomposeVAppParams>"""%(currentVapp.name, self.href, newName, newName, self.href, network)

		self.headers["Content-Type"] = "application/vnd.vmware.vcloud.recomposeVAppParams+xml"
		response = requests.post(currentVapp.href+"/action/recomposeVApp", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			if lock:
				#Get the task href
				href = root.get("href")
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)
				while root.get("status") != "success":
					time.sleep(1)
					response = requests.get(href, headers = self.headers)
					root = ET.fromstring(response.text)

			return 0


	def consolidate(self):
		""" Consolide VM disk """

		response = requests.post(self.href+"/action/consolidate", headers = self.headers)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0




class vAPP:
	'vAPP Class'

	def __init__(self,href, name, vdc):
		self.href = href
		self.name = name
		self.vdc_url = vdc
		self.vms = {}




class vDC:
	'Virtual Datacenter Class'

	def __init__(self, href, name):
		self.href = href
		self.name = name
		self.response = ""
		self.vapps = {}


class edgeGateway:
	'Edge Gateway'

	def __init__(self, headers, href, name, status, vdc_url ):
		self.headers = headers
		self.href = href
		self.name = name
		self.status = status
		self.vdc_url = vdc_url
		self.response = requests.get(self.href, headers = self.headers)
		#pprint(response.text)
		#Register Namespace in order to avoid "ns0:"
		ET.register_namespace('', "http://www.vmware.com/vcloud/v1.5")
		root = ET.fromstring (self.response.text)
		#Edge Gateway Full Configuration
		self.config = root.findall('.//{http://www.vmware.com/vcloud/v1.5}EdgeGatewayServiceConfiguration')[0]

	def print_config(self):
		pprint(ET.dump(self.config))

	def get_config(self):
		return self.config

	def get_nat_config(self):
		config = self.get_config()
		#Nat Rules
		nat = config.find('{http://www.vmware.com/vcloud/v1.5}NatService')
		#pprint(ET.dump(nat))
		return nat

	def get_firewall_config(self):
		config = self.get_config()
		#Firewall Rules
		firewall = config.find('{http://www.vmware.com/vcloud/v1.5}FirewallService')
		#pprint(ET.dump(firewall))
		return firewall

	def get_nat_rules(self):
		nat = self.get_nat_config()
		rules = list(nat.iter('{http://www.vmware.com/vcloud/v1.5}NatRule'))
		#pprint(rules)
		return rules

	def add_snat_rule(self, rule_name, network, public_ip, private_ip, vorg ):

		net = vorg.get_vorg_network(network)
		network_url = net.get_url()

		nat = self.get_nat_config()
		xml_data = """<NatRule>
			<Description>%s</Description>
			<RuleType>SNAT</RuleType>
			<IsEnabled>true</IsEnabled>
			<Id>65552</Id>
			<GatewayNatRule>
				<Interface href="%s" name="%s" type="application/vnd.vmware.admin.network+xml" />
				<OriginalIp>%s</OriginalIp>
				<TranslatedIp>%s</TranslatedIp>
			</GatewayNatRule>
		</NatRule>
		"""%(rule_name, network_url, network, private_ip, public_ip)

		nat.append(ET.fromstring(xml_data))

		xml_data = ET.tostring(self.config).decode("utf-8")

		self.headers["Content-Type"] = "application/vnd.vmware.admin.edgeGatewayServiceConfiguration+xml"
		response = requests.post(self.href+"/action/configureServices", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		#pprint(response.text)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0

		#pprint(ET.dump(nat))


	def remove_snat_rule(self, rule_name):
		""" Delete SNAT Rule by Description, it delete all the rules with the same description name """

		nat = self.get_nat_config()
		rules = self.get_nat_rules()

		for rule in rules:
			desc = rule.find('{http://www.vmware.com/vcloud/v1.5}Description')
			type = rule.find('{http://www.vmware.com/vcloud/v1.5}RuleType')
			if desc != None and type.text == "SNAT":
				if desc.text == rule_name:
					nat.remove(rule)

		xml_data = ET.tostring(self.config).decode("utf-8")

		self.headers["Content-Type"] = "application/vnd.vmware.admin.edgeGatewayServiceConfiguration+xml"
		response = requests.post(self.href+"/action/configureServices", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		#pprint(response.text)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0



	def add_dnat_rule(self, rule_name, network, public_ip, public_port, private_ip, private_port, vorg):

		net = vorg.get_vorg_network(network)
		network_url = net.get_url()

		nat = self.get_nat_config()
		xml_data = """<NatRule>
			<Description>%s</Description>
			<RuleType>DNAT</RuleType>
			<IsEnabled>true</IsEnabled>
			<Id>63554</Id>
			<GatewayNatRule>
				<Interface href="%s" name="%s" type="application/vnd.vmware.admin.network+xml" />
				<OriginalIp>%s</OriginalIp>
				<OriginalPort>%s</OriginalPort>
				<TranslatedIp>%s</TranslatedIp>
				<TranslatedPort>%s</TranslatedPort>
				<Protocol>tcp</Protocol>
			</GatewayNatRule>
		</NatRule>
		"""%(rule_name, network_url, network, public_ip, public_port, private_ip, private_port)

		# pprint(xml_data)

		nat.append(ET.fromstring(xml_data))

		xml_data = ET.tostring(self.config).decode("utf-8")

		self.headers["Content-Type"] = "application/vnd.vmware.admin.edgeGatewayServiceConfiguration+xml"
		response = requests.post(self.href+"/action/configureServices", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		#pprint(response.text)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0

		#pprint(ET.dump(nat))


	def remove_dnat_rule(self, rule_name):
		""" Delete DNAT Rule by Description, it delete all the rules with the same description name """

		nat = self.get_nat_config()
		rules = self.get_nat_rules()

		for rule in rules:
			desc = rule.find('{http://www.vmware.com/vcloud/v1.5}Description')
			type = rule.find('{http://www.vmware.com/vcloud/v1.5}RuleType')
			if desc != None and type.text == "DNAT":
				if desc.text == rule_name:
					nat.remove(rule)

		xml_data = ET.tostring(self.config).decode("utf-8")

		self.headers["Content-Type"] = "application/vnd.vmware.admin.edgeGatewayServiceConfiguration+xml"
		response = requests.post(self.href+"/action/configureServices", headers = self.headers, data = xml_data)
		self.headers.pop("Content-Type")
		#pprint(response.text)
		root = ET.fromstring(response.text)
		if response.status_code != 202:
			return -1
		else:
			#Get the task href
			href = root.get("href")
			response = requests.get(href, headers = self.headers)
			root = ET.fromstring(response.text)
			while root.get("status") != "success":
				time.sleep(1)
				response = requests.get(href, headers = self.headers)
				root = ET.fromstring(response.text)

			return 0



class vorgNetwork:
	""" vOrg Network """

	def __init__(self, headers, href, name ):
		self.headers = headers
		self.href = href
		self.name = name

	def get_url(self):
		return self.href

	def print_config(self):
		pprint(self.name)
		pprint(self.href)


class vORG:
	'Virtual Organization Class'

	def __init__(self):
		self.headers = {'Accept': 'application/*+xml;version=5.6'}
		self.href = ""
		self.session_response = ""
		self.org_response = ""
		self.vdcs = {}
		self.vapps = {}
		self.vms = {}
		self.url = ""


	def login(self, url, user, password, org):
		"""Get API Token"""
		self.url = url
		login = (user+'@'+org,password)
		#Login to API
		self.session_response = requests.post(self.url+"/api/sessions", headers = self.headers, auth=login)
		#pprint(self.session_response)
		#Get Token
		self.headers['x-vcloud-authorization'] = self.session_response.headers['x-vcloud-authorization']
		root = ET.fromstring(self.session_response.text)
		for child in root:
			try:
				if(child.attrib['type'] == "application/vnd.vmware.vcloud.org+xml"):
					self.href = child.attrib['href']
			except:
				pass

	def get_vdcs(self):
		self.vdcs = {}
		self.org_response = requests.get(self.href, headers = self.headers)
		root = ET.fromstring(self.org_response.text)
		for child in root:
			try:
				if(child.attrib['type'] == "application/vnd.vmware.vcloud.vdc+xml"):
					href = child.attrib['href']
					name = child.attrib['name']
					vdc = vDC(href, name)
					self.vdcs[name] = vdc
			except:
				pass
		return self.vdcs

	def getVapps(self):
		self.vapps = {}
		response = requests.get(self.url+"/api/query?type=vApp", headers = self.headers)
		root = ET.fromstring(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VAppRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vdc = child.attrib['vdc']
			vapp = vAPP(href, name, vdc)
			self.vapps[name] = vapp
		return self.vapps

	def getVapp(self, name):
		vapp = ""
		response = requests.get(self.url+'/api/query?type=vApp&filter=(name=='+name+')', headers = self.headers)
		root = ET.fromstring(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VAppRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vdc = child.attrib['vdc']
			vapp = vAPP(href, name, vdc)
		return vapp

	def getAllVMs(self):
		""" Get all the VM's into the vOrg """
		self.vms = {}
		response = requests.get(self.url+'/api/query?type=vm&filter=(isVAppTemplate==false)', headers = self.headers)
		root = ET.fromstring(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VMRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vapp = child.attrib['containerName']
			vapp_url = child.attrib['container']
			try:
				network = child.attrib['networkName']
			except:
				network = ""
			try:
				network_url = child.attrib['network']
			except:
				network_url = ""
			storage_profile = child.attrib['storageProfileName']
			vdc_url = child.attrib['vdc']
			vm = VM(self.headers, href, name, vapp, vapp_url, network, network_url, storage_profile, vdc_url)
			self.vms[name] = vm
		return self.vms


	def getVMsRegExp(self, name, vapp="*"):
		""" Get all VMs filtered by root name """

		vms = {}
		response = requests.get(self.url+'/api/query?type=vm&filter=(name=='+name+'*;containerName=='+vapp+')', headers = self.headers)
		root = ET.fromstring(response.text)
		# pprint(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VMRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vapp = child.attrib['containerName']
			vapp_url = child.attrib['container']
			try:
				network = child.attrib['networkName']
			except:
				network = ""
			try:
				network_url = child.attrib['network']
			except:
				network_url = ""
			storage_profile = child.attrib['storageProfileName']
			vdc_url = child.attrib['vdc']
			vms[name] = VM(self.headers, href, name, vapp, vapp_url, network, network_url, storage_profile, vdc_url)
		return vms


	def getPowerOnVMsRegExp(self, name, vapp="*"):
		""" Get powered ON VMs filtered by root name """

		vms = {}
		response = requests.get(self.url+'/api/query?type=vm&filter=(name=='+name+'*;containerName=='+vapp+';status==POWERED_ON)', headers = self.headers)
		root = ET.fromstring(response.text)
		# pprint(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VMRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vapp = child.attrib['containerName']
			vapp_url = child.attrib['container']
			try:
				network = child.attrib['networkName']
			except:
				network = ""
			try:
				network_url = child.attrib['network']
			except:
				network_url = ""
			storage_profile = child.attrib['storageProfileName']
			vdc_url = child.attrib['vdc']
			vms[name] = VM(self.headers, href, name, vapp, vapp_url, network, network_url, storage_profile, vdc_url)
		return vms


	def getVM(self, name, vapp="*"):
		""" Get one VM by name """

		vm =""
		response = requests.get(self.url+'/api/query?type=vm&filter=(name=='+name+';containerName=='+vapp+')', headers = self.headers)
		root = ET.fromstring(response.text)
		# pprint(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VMRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vapp = child.attrib['containerName']
			vapp_url = child.attrib['container']
			try:
				network = child.attrib['networkName']
			except:
				network = ""
			try:
				network_url = child.attrib['network']
			except:
				network_url = ""
			storage_profile = child.attrib['storageProfileName']
			vdc_url = child.attrib['vdc']
			vm = VM(self.headers, href, name, vapp, vapp_url, network, network_url, storage_profile, vdc_url)
		return vm


	def getTemplate(self,name):
		""" Get template VM """

		vm = ""
		response = requests.get(self.url+'/api/query?type=vm&filter=(isVAppTemplate==true;name=='+name+')', headers = self.headers )
		root = ET.fromstring(response.text)
		# pprint(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}VMRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vapp = child.attrib['containerName']
			vapp_url = child.attrib['container']
			try:
				network = child.attrib['networkName']
			except:
				network = ""
			try:
				network_url = child.attrib['network']
			except:
				network_url = ""
			storage_profile = child.attrib['storageProfileName']
			vdc_url = child.attrib['vdc']
			vm = VM(self.headers, href, name, vapp, vapp_url, network, network_url, storage_profile, vdc_url)
		return vm

	def get_edge_gateway(self,name):
		""" Get Edge Gateway Firewall """

		edge = ""
		response = requests.get(self.url+'/api/query?type=edgeGateway&filter=(name=='+name+')', headers = self.headers )
		root = ET.fromstring(response.text)
		# pprint(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}EdgeGatewayRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			gatewayStatus = child.attrib['gatewayStatus']
			vdc_url = child.attrib['vdc']
			edge = edgeGateway(self.headers, href, name, gatewayStatus, vdc_url)
		return edge


	def get_vorg_network(self, name):
		""" Get vOrg Network """

		vorg_network = ""
		response = requests.get(self.url+'/api/query?type=orgNetwork&filter=(name=='+name+')', headers = self.headers )
		root = ET.fromstring(response.text)
		# pprint(response.text)
		for child in root.findall('{http://www.vmware.com/vcloud/v1.5}OrgNetworkRecord'):
			href = child.attrib['href']
			name = child.attrib['name']
			vorg_network = vorgNetwork(self.headers, href, name )
		return vorg_network



	def xml(self):
		"""Get XML response"""
		pprint(self.session_response.text)
		pprint(self.org_response.text)




#!/usr/bin/env python

# Module import
import sys
import yaml
from  elastic_api import *
import os
import requests
import datetime
import time


# Date
#import time
#print time.strftime("%Y-%m-%d %H:%M:%S")
try:
	response = requests.get("http://just-the-time.appspot.com/")
	expiration_date = str(datetime.datetime(2019, 11, 2, 11, 00, 00))+" "
	if response.text > expiration_date:
		print("Demo time expired")
		exit(9)
except:
	print("There is no internet connexion")
	exit(10)



# Load config file

if len(sys.argv) < 2:
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": It's necessary introduce the config file as a parameter")
	exit(1)


config={}
with open(sys.argv[1], 'r') as stream:
    try:
        config = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(time.strftime("%Y-%m-%d %H:%M:%S")+" Error parsing parameters: "+exc)
        exit(2)

#Check min and max node parameter
if (config['min_compute_nodes'] < 1) or (config['max_compute_nodes'] < 2) or (config['min_compute_nodes'] == config['max_compute_nodes']):
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": Check the MIN and MAX parameter values:")
	print("MIN >= 1")
	print("MAX >= 2")
	print("MIN > MAX")
	exit(1)


# Generate Lock file

lock_file = sys.argv[1].split(".")[0]+".lock"

if os.path.isfile('./'+lock_file):
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": There is another process running")
	exit(1)



def salir(estado):
	os.remove('./'+lock_file)
	exit(estado)


###
# Main program
###

file = open(lock_file,"w")
file.close()

vorg = vORG()
vorg.login(config['URL'],config['user'], config['pass'], config['vorg'])


# Get the Template VM
templateVm = vorg.getTemplate(config['template_name'])

# Get the elastic VM's
elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

###
# If there are no elastic nodes, create the firs one, powered it on, and the second in standby mode
###
if len(elasticVMs) == 0:
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": There is no elastic nodes, creating the first one.")
	# First server
	name = config['compute_nodes_name']+"1"
	result = templateVm.cloneVm( name, vorg, config['vapp'], config['network'] )

	# If there is an error, exit
	if result != 0:
		print(time.strftime("%Y-%m-%d %H:%M:%S")+": Error al clonar la VM")
		salir(1)

	elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
	elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

	vm = vorg.getVM(name, config['vapp'])
	vm.powerOn()

	# Creating SNAT and DNAT
	edge = vorg.get_edge_gateway(config['edge_name'])
	edge.add_snat_rule(vm.name ,config['edge_network'], config['public_ip'], vm.getIP(), vorg)
	public_port = config['starting_public_port']+len(elasticVMs)
	edge.add_dnat_rule(vm.name, config['edge_network'], config['public_ip'], public_port, vm.getIP(), config['private_port'], vorg)

	# Second server
	name = config['compute_nodes_name']+"2"
	result = templateVm.cloneVm( name, vorg, config['vapp'], config['network'] )

	# If there is an error, salir
	if result != 0:
		print(time.strftime("%Y-%m-%d %H:%M:%S")+": Error al clonar la VM")
		salir(1)

	elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
	elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

	vm = vorg.getVM(name, config['vapp'])

	# Creating SNAT and DNAT
	edge = vorg.get_edge_gateway(config['edge_name'])
	edge.add_snat_rule(vm.name ,config['edge_network'], config['public_ip'], vm.getIP(), vorg)
	public_port = config['starting_public_port']+len(elasticVMs)
	edge.add_dnat_rule(vm.name, config['edge_network'], config['public_ip'], public_port, vm.getIP(), config['private_port'], vorg)


# Get the elastic VM's
elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])


###
# If min nodes are not enough, create them
###
while len(elasticPowerOnVMs) < config['min_compute_nodes']:
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": The min nodes are not enough, creating another one.")
	# We turn on the standby node
	name = config['compute_nodes_name']+str(len(elasticVMs))
	vm = vorg.getVM(name, config['vapp'])
	vm.powerOn()

	# and create another standby node.
	serverNumber = len(elasticVMs)+1
	name = config['compute_nodes_name']+str(serverNumber)
	result = templateVm.cloneVm( name, vorg, config['vapp'], config['network'] )

	# If there is an error, salir
	if result != 0:
		print(time.strftime("%Y-%m-%d %H:%M:%S")+": Error al clonar la VM")
		salir(1)

	elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
	elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

	vm = vorg.getVM(name, config['vapp'])

	# Creating SNAT and DNAT
	edge = vorg.get_edge_gateway(config['edge_name'])
	edge.add_snat_rule(vm.name ,config['edge_network'], config['public_ip'], vm.getIP(), vorg)
	public_port = config['starting_public_port']+len(elasticVMs)
	edge.add_dnat_rule(vm.name, config['edge_network'], config['public_ip'], public_port, vm.getIP(), config['private_port'], vorg)



###
# Get CPU & MEM averages
###

cpu_load_total = 0
cpu_load_avg = 0
mem_load_total = 0
mem_load_avg = 0
for vm_name in elasticPowerOnVMs.keys():
	cpu_load_total += float( elasticPowerOnVMs[vm_name].getCpuUsage() )
	mem_load_total += float( elasticPowerOnVMs[vm_name].getMemUsage() )

cpu_load_avg = cpu_load_total/len(elasticPowerOnVMs)
mem_load_avg = mem_load_total/len(elasticPowerOnVMs)


#print(cpu_load_avg)
#print(mem_load_avg)



###
# Check CPU load to increase nodes.
###
if (cpu_load_avg >= config['increase_percentage']) and (len(elasticPowerOnVMs) < config['max_compute_nodes']):
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": CPU load average over "+str(config['increase_percentage'])+". Creating node.")
	# We turn on the standby node, we do in this way in case there are more than one standby nodes
	name = config['compute_nodes_name']+str(len(elasticPowerOnVMs)+1)
	vm = vorg.getVM(name, config['vapp'])
	vm.powerOn()
	if len(elasticVMs) < config['max_compute_nodes']:
		name = config['compute_nodes_name']+str(len(elasticVMs)+1)
		result = templateVm.cloneVm( name, vorg, config['vapp'], config['network'] )
		# If there is an error, salir
		if result != 0:
			print(time.strftime("%Y-%m-%d %H:%M:%S")+": Error al clonar la VM")
			salir(1)

		elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
		elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

		vm = vorg.getVM(name, config['vapp'])

		# Creating SNAT and DNAT
		edge = vorg.get_edge_gateway(config['edge_name'])
		edge.add_snat_rule(vm.name ,config['edge_network'], config['public_ip'], vm.getIP(), vorg)
		public_port = config['starting_public_port']+len(elasticVMs)
		edge.add_dnat_rule(vm.name, config['edge_network'], config['public_ip'], public_port, vm.getIP(), config['private_port'], vorg)

	salir(0)



###
# Check MEM load to increase Nodes.
###
if (mem_load_avg >= config['increase_percentage']) and (len(elasticPowerOnVMs) < config['max_compute_nodes']):
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": MEM load average over "+str(config['increase_percentage'])+". Creating node.")
	# We turn on the standby node, we do in this way in case there are more than one standby nodes
	name = config['compute_nodes_name']+str(len(elasticPowerOnVMs)+1)
	vm = vorg.getVM(name, config['vapp'])
	vm.powerOn()
	if len(elasticVMs) < config['max_compute_nodes']:
		name = config['compute_nodes_name']+str(len(elasticVMs)+1)
		result = templateVm.cloneVm( name, vorg, config['vapp'], config['network'] )
		# If there is an error, salir
		if result != 0:
			print(time.strftime("%Y-%m-%d %H:%M:%S")+": Error al clonar la VM")
			salir(1)

		elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
		elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

		vm = vorg.getVM(name, config['vapp'])

		# Creating SNAT and DNAT
		edge = vorg.get_edge_gateway(config['edge_name'])
		edge.add_snat_rule(vm.name ,config['edge_network'], config['public_ip'], vm.getIP(), vorg)
		public_port = config['starting_public_port']+len(elasticVMs)
		edge.add_dnat_rule(vm.name, config['edge_network'], config['public_ip'], public_port, vm.getIP(), config['private_port'], vorg)

	salir(0)



###
# Check CPU load to decrease nodes.
###
if (cpu_load_avg <= config['decrease_percentage']) and (mem_load_avg <= config['decrease_percentage']) and (len(elasticPowerOnVMs) > config['min_compute_nodes']):
	# We turn on the standby node, we do in this way in case there are more than one standby nodes
	print(time.strftime("%Y-%m-%d %H:%M:%S")+": CPU and MEM load average above "+str(config['decrease_percentage'])+". Deleting node.")
	name = config['compute_nodes_name']+str(len(elasticVMs))
	vm = vorg.getVM(name, config['vapp'])

	# Remove SNAT and DNAT Rules
	edge = vorg.get_edge_gateway(config['edge_name'])
	edge.remove_snat_rule(vm.name)
	edge.remove_dnat_rule(vm.name)

	vm.powerOffUndeploy()
	#Delete VM
	if len(elasticPowerOnVMs) < len(elasticVMs):
		name = config['compute_nodes_name']+str(len(elasticVMs))
		vm = vorg.getVM(name, config['vapp'])
		vm.deleteVm()

	elasticVMs = vorg.getVMsRegExp(config['compute_nodes_name'])
	elasticPowerOnVMs = vorg.getPowerOnVMsRegExp(config['compute_nodes_name'])

	#PowerOff
	name = config['compute_nodes_name']+str(len(elasticVMs))
	vm = vorg.getVM(name, config['vapp'])

	vm.powerOff()

	salir(0)



print(time.strftime("%Y-%m-%d %H:%M:%S")+": Exit, nothing to do")
salir(0)

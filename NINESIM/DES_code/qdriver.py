#/////////////////////////////
# Queueing Model Use qdriver
#/////////////////////////////

import sys
from sys import path
from SimianPie.simian import Simian
import qmodel

from constants import conops

#############
# Parameters (replace with conops in advanced version)

params = {
"NUM_RUNS"				: 1,
"NUM_QNODES"			: 7, 
"QMAX"                  : [1000000, 1000000, 10, 10, 10, 10, 1], # maximum number of vehicles on in-queues
"NUM_VEHICLES" 			: 1000,
"SOURCE_VEHICLE_IDS"	: [7, 25],
"p"                     : 0.1,                              # probability of being sent to secondary
"mean_arrival"          : 0.75,                              # mean time between arrivals
"mean_primary"          : 2,                                # mean time in primary
"mean_secondary"        : 2,                                # mean time in secondary
"transit_time"          : .1                                # time to drive to a queue
}
#############

for sim in range(params["NUM_RUNS"]):
    #Simian-specific syntax
    simName, startTime, endTime, minDelay, useMPI = "NineSIM", 0, 1000000000, 1, False
    simianEngine = Simian(simName, startTime, endTime, minDelay, useMPI)
    
    # Create QNODE Entities
    for i in range(params["NUM_QNODES"]):
    	simianEngine.addEntity("qnode", qmodel.qNode, i, params)
    
    # Create VEHICLE Entities
    for i in range(params["NUM_VEHICLES"]):
    	simianEngine.addEntity("Vehicle", qmodel.Item, i, params["p"], params["transit_time"])
    	
	# QNode 0 accepts all vehicles into its in_q
    qnode = simianEngine.getEntity("qnode", 0)
    for i in range(params["NUM_VEHICLES"]):
	 	vehicle = simianEngine.getEntity("Vehicle", i)
	 	qnode.insertItem(vehicle)
	 	
    # Start eventCall the processNext function to get going
    simianEngine.schedService(startTime, "processNext", [] , "qnode", 0)
	 
	# Start Simian	
    simianEngine.run()
    simianEngine.exit()
    
    
    
   

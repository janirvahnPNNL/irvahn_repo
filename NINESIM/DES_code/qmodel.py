
#/////////////////////////////
#Base classes for a queueing model
#Node Entity
#/////////////////////////////

#Added datetime as an input to all distributions allowing for dattime dependence 
#from SimianPie.simian import Entity
#from auxfunctions import getDist, getVelocity, getCoords, getDescription, linDistance, getDatetime 
#from distributions import runDistribution
import sys
from constants import conops
from sys import path
import numpy
#path.append('SimianPie')

#from simian import Simian 
from SimianPie.simian import Simian
from SimianPie.entity import Entity

import random

# Next three functions are custom functions that use the conops data structure
# For now, I put in something highly random. You'll need to replace with conops magic here

def determineDelay(data, params):
	# Gets called when a qnode starts processing an item
	# Return a time delay value
    # data is data = [qnode_id, item, qnode.state] 
    
    num_qnodes = params["NUM_QNODES"]
    id = data[0]
    item = data[1]
    state = data[2]
    delay = 10# random.randint(0, 100)

    #
    # what is the state of the system when the jth vehicle arrives? 
    j=99
    if(id==1 and item.id==j):
        print("Vehicle ",item.id," arrived")
        print("The arrival queue has",len(item.engine.entities["qnode"][1].in_q),"vehicles (not counting vehicle ",item.id,")")
        print("Primary, lane 1 queue has",len(item.engine.entities["qnode"][3].in_q),"vehicles")
        print("Primary, lane 2 queue has",len(item.engine.entities["qnode"][4].in_q),"vehicles")
        print("Primary, lane 3 queue has",len(item.engine.entities["qnode"][5].in_q),"vehicles")
        print("Secondary queue has",      len(item.engine.entities["qnode"][7].in_q),"vehicles")
        print("Primary, lane 1 is processing: ",item.engine.entities["qnode"][3].processing)
        print("Primary, lane 2 is processing: ",item.engine.entities["qnode"][4].processing)
        print("Primary, lane 3 is processing: ",item.engine.entities["qnode"][5].processing)
        print("Secondary is processing: ",item.engine.entities["qnode"][7].processing)
    #
    #

    if id == 0:
        delay = random.expovariate(1.0 / params["mean_arrival"])
    if id == 1:
        delay = 0
    if id in (2,6,8):
        delay = params["transit_time"]
    if id in (3,4,5):
        delay = random.expovariate(1.0 / params["mean_primary"])
    if id == 7:
        delay = random.expovariate(1.0 / params["mean_secondary"])
    return delay


def determineNextQ(data, params):
	# Gets called when a qnode is done processing an item
	# Return a qnode_id for the next qnode it is sent to
    # data is data = [qnode_id, item, qnode.state] 
    
    num_qnodes = params["NUM_QNODES"]
    id = data[0]
    sfs = data[1].sfs
    state = data[2]
    qnode_id = "terminal"
    if id==0:                          # if source (0), send to arrival (1)
        qnode_id = 1
    if id==1:                          # if arrival (1), send to transit node (2)
        qnode_id = 2
    if id==2:                          # if transit node (2), send to primary (3,4,5)
        primary_queue_lengths=[len(data[1].engine.entities["qnode"][3].in_q),
            len(data[1].engine.entities["qnode"][4].in_q),
            len(data[1].engine.entities["qnode"][5].in_q)]
        pqm = params["QMAX"][3:6]
        for i in range(0,len(primary_queue_lengths)):
            if(primary_queue_lengths[i]>=pqm[i]):
                primary_queue_lengths[i]=2*max(pqm)      # if lane is full, 'disqualify'
        qnode_id = 3+numpy.argmin(primary_queue_lengths) # 3 lanes at primary: pick the first of the non-full shortest queues
    if id in (3,4,5) and sfs==1:       # if primary AND alarm, send to transit node (6)
        qnode_id = 6
    if id in (3,4,5) and sfs==0:       # if primary AND no alarm, send to transit node (8) 
        qnode_id = 8
    if id==6:                          # if transit node (6), send to secondary(7)
        qnode_id = 7
    if id==7:                          # if secondary (7), send to transit node (8)
        qnode_id = 8
    return qnode_id
    
    
def determineStateChanges(data, params):
	# Gets called each time an item starts getting processed by a qnode
	# Returns two list qnode_ids and states of new states for the qnode_ids
    # data is data = [qnode_id, item, qnode.state] 
    num_qnodes = params["NUM_QNODES"]
    item_id = data[1].id
    if item_id in params["SOURCE_VEHICLE_IDS"]:
        bad_item = True
    else:
        bad_item = False
    qnode_ids, states = [], []
    if bad_item:
    	qnode_ids = [0, 1, 2]
    	states = ["alarm", "alarm", "alarm"]
    else:
        qnode_ids = [0, 1, 2]
        states = ["normal", "normal", "normal"]
    return (qnode_ids, states)

#############
class Item(Entity):
#
#Items are the objects that are moved through the queues
#
    def __init__(self, id, p):
        super(Item, self).__init__(id)
        self.id = self.num
        self.sfs = numpy.random.binomial(1,p,1) # slated for secondary: 0 means no, 1 means yes
        #print self,  " created "

        
class qNode(Entity):
#
# A qnode is a queueing node that has an input queue. A qnode processes the first item
# in its input queue and then passes the tiem on to a follow-on q
#
    def __init__(self, baseInfo, params):
        super(qNode, self).__init__(baseInfo)
        self.id = self.num              # id from the base class of entity
        self.in_q = []                  # input queue
        self.out_q = []                 # out queue
        self.params = params            # params is the global data storage
        self.qmax = params["QMAX"][self.id]   # max queue size
        self.processing = False         # Flag indicating if node is currently processing an 
                                        # item
        self.state = "normal"           # state has an effect on processing times
                                        # from a set of eg ["normal", "alarm", ...]
        self.waiting_qnodes = []        # list of qnodes that this node needs to inform 
                                        # once its in_q is no longer at qmax

    def processNext(self, *args):
    #
    # Processes next item in_queue event. 
    # Empties the single item in the out_queue first (if any).
    # Calls functions to determine processing time, follow-on q, and state changes
    #
        #print self.engine.now, ": ", self,  " with q_out, qin", len(self.out_q), len(self.in_q)
        # 0. Try to empty out_queue
        if len(self.out_q) > 0: # at most one item should be in the out queue
            [dispatchtime, item] =  self.out_q[len(self.out_q) -1]
            dest_id = determineNextQ([self.id, item, self.state], self.params)
            #print self.engine.now, ": ", self,  " with  [dispatchtime, dest_id, item]", dispatchtime, dest_id, item
            if dest_id == "terminal":
                # this item is done, we are removing it from the queueing system
                self.out_q.pop()
                self.processing = False
                print self.engine.now, ": ", self,  " terminated ", item
            elif dispatchtime <= self.engine.now:  # I can try to send this out
                dest_qnode = self.engine.getEntity("qnode", dest_id)
                if dest_qnode.insertItem(item, self):
                    self.out_q.pop() # remove from q only if successfully inserted
                    print self.engine.now, ": ", self,  " sent ", item, " to qnode ", dest_id
                    self.processing = False
                else:
                    self.processing = True
                    print self.engine.now, ": ", self,  " returns ", item , " into own out q"
                    return 
                    # backpressure congestion, so this node gets stuck until processNext
                    # is called again by the downstream node
            else:
            	# We had unnecessary invocation of processNext
            	return
        
        # 1. Check in_queue
        if len(self.in_q) > 0:
            # 2. Pop
            item = self.in_q.pop()
            data = [self.id, item, self.state]
            delay = determineDelay(data, self.params)
            print self.engine.now, ": ", self,  " processing vehicle ", item, " with delay ", delay
            # 3. Put into out queue
            self.out_q.append([self.engine.now+delay, item])
            # 4. Schedule myself in the future
            self.processing = True
            self.reqService(delay, "processNext", [])
            # 5. Update state changes
            (qnode_ids, states) = determineStateChanges(data, self.params)
            for i in range(len(qnode_ids)):
                dest_qnode = self.engine.getEntity("qnode", qnode_ids[i])
                dest_qnode.changeState(states[i])
                # If parallel desired, replace with an event call as follows
                # self.reqService(minDelay, "changeState", states[i], "qNode", i)           
            # 6. Inform waiting queues that there is space now.
            while (len(self.waiting_qnodes) > 0) and (len(self.in_q) <= self.qmax):
                qnode = self.waiting_qnodes.pop()
                print self.engine.now, ": ", self,  " wakes up Qnode ", qnode.num, " to remind it"
                qnode.processNext()
        else: # Queue is empty
            self.processing = False
            
            
            
    def changeState(self, newState):
    #
    #Change state
    #
        self.state = newState
    

    def insertItem(self, item, sender_qnode = None):
    #
    #InsertItem into local q 
    #
        if len(self.in_q) >= self.qmax:
            self.waiting_qnodes.insert(0, sender_qnode)
            print self.engine.now, ": ", self,  " refuses ", item
            return False
        else:
            self.in_q.insert(0, item)
            print self.engine.now, ": ", self,  " accepted item ", item
            if not self.processing: # We have to wake ourselves up
                self.processNext()
            return True

         
                                                          

"""
Created on Oct 12, 2016

@author: mwitt_000
"""
import queue
import threading
import pandas as pd
import sys


# wrapper class for a queue of packets
class Interface:
    # @param maxsize - the maximum size of the queue storing packets
    #  @param cost - of the interface used in routing
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize);
        self.out_queue = queue.Queue(maxsize);

    # get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                #                 if pkt_S is not None:
                #                     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                #                 if pkt_S is not None:
                #                     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    # put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            #
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


# Implements a network layer packet
# Todo: NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
# We can have a data packet or a control packet that contains a routing table.
class NetworkPacket:
    # packet encoding lengths
    source_addr_S_length = 1
    dst_addr_S_length = 2
    prot_S_length = 1

    header_length = source_addr_S_length + dst_addr_S_length + prot_S_length

    # @param source_addr: address of the source node, could be a host or a router.
    # @param dst_addr: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, source_addr, dst_addr, prot_S, data_S):
        self.source_addr = source_addr
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.prot_S = prot_S

    # called when printing the object
    def __str__(self):
        return self.to_byte_S()

    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.source_addr)
        byte_S += str(self.dst_addr).zfill(self.dst_addr_S_length)
        if self.prot_S == 'data':  # data
            byte_S += '1'
        elif self.prot_S == 'control':  # routing table
            byte_S += '2'
        else:
            raise ('%s: unknown prot_S option: %s' % (self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        source_addr = byte_S[0: NetworkPacket.source_addr_S_length]
        dst_addr = int(byte_S[NetworkPacket.source_addr_S_length:NetworkPacket.source_addr_S_length + NetworkPacket.dst_addr_S_length])
        prot_S = byte_S[3:4]
        if prot_S == '1':
            prot_S = 'data'

        elif prot_S == '2':
            prot_S = 'control'

        else:
            raise ('%s: unknown prot_S field: %s' % (self, prot_S))

        data_S = byte_S[NetworkPacket.header_length:]
        return self(source_addr, dst_addr, prot_S, data_S)


# Skeleton of the Message class that will send a router table update
# Todo: figure out message format, and length
# Todo: write the to_byte_S and from_byte_s methods
# This will take in a routing table, convert it into a string format to send
# reconvert it from string to a readable table again.
class UpdateMessage:

    message_S_length = 3

    # constructor
    def __init__(self, dictionary_table):
        self.message = dictionary_table

    # convert a message to a byte string for sending message to add to the packet?
    def to_byte_S(self):
        byte_S = ''
        table = self.message
        for destination in table:
            byte_S += str(destination)
            for interface in table[destination]:
                byte_S += str(interface)
                cost = table[destination][interface]
                byte_S += str(cost)
        byte_S = byte_S.zfill(self.message_S_length) 
        return byte_S

    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        destination = int(byte_S[0])
        if byte_S[1] == '~':
            interface = float('inf')
        else:
            interface = int(byte_S[1])
        cost = int(byte_S[2])
        table = {destination: {interface: cost}}
        return table


# Implements a network host for receiving and transmitting data
class Host:
    # @param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False  # for thread termination

    # called when printing the object
    def __str__(self):
        return 'Host_%s' % self.addr

    # create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S):
        p = NetworkPacket(self.addr, dst_addr, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out')  # send packets always enqueued successfully

    # receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    # thread target for the host to keep receiving data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return


# Implements a multi-interface router described in class
class Router:
    # ##@param name: friendly router name for debugging
    #  @param num_intf: number of bidirectional interfaces
    #  @param rt_tbl_D: routing table dictionary (starting reachablility), eg. {1: {1: 1}}
    #  packet to host 1 through interface 1 for cost 1
    #  @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, num_intf, rt_tbl_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        # note the number of interfaces is set up by out_intf_cost_L
        self.intf_L = []
        for i in range(num_intf):
            self.intf_L.append(Interface(max_queue_size))
        # set up the routing table for connected hosts
        self.rt_tbl_D = rt_tbl_D
        # called when printing the object

    def __str__(self):
        return 'Router_%s' % (self.name)

    # look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):

            # get packet from interface i
            pkt_S = self.intf_L[i].get('in')

            # if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p, i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))

    # forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the 
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is (i+1)%2
            self.intf_L[(i+1)%2].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % (self, p, i, (i+1)%2))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    # This is called if a router has received a control packet from a neighboring router signaling a need to update it's own router.
    # It will also need to create a new update and sent it to its neighboring routers using sendRoutes()
    # Implement DV algorithm here.
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        # TODO: add logic to update the routing table and possibly send out more routing updates
        neighbor_table = UpdateMessage.from_byte_S(p.data_S)
        neighboring_router = p.source_addr

        print('%s: Received routing update %s through interface %d, from router %s' % (self, p, i, neighboring_router))
        w,x,y,z = float('Inf'),float('Inf'),float('Inf'),float('Inf')
        w1,x1,y1,z1 = float('Inf'),float('Inf'),float('Inf'),float('Inf')
        temp = self.rt_tbl_D

        #the 1 and 2 belonging to temp represents the columns of the routing table
        # the 0 and 1 in payload represent the interfaces, therefore based on the interfaces and columns we know which element to update with the payload
        if 1 in temp: #temp is the current routing table
            payload = temp.get(2)
            if 0 in payload:
                w = payload.get(0)
            if 1 in payload:
                y = payload.get(1)

        if 2 in temp:
            payload = temp.get(2)
            if 0 in payload:
                x = payload.get(0)
            if 1 in payload:
                z = payload.get(1)

        if 1 in neighbor_table: #this is the table that was passed that we need to update with
            payload = neighbor_table.get(1)
            if 0 in payload:
                w1 = payload.get(0)
            if 1 in payload:
                y1 = payload.get(1)

        if 2 in neighbor_table:
            payload = neighbor_table.get(1)
            if 0 in payload:
                x1 = payload.get(0)
            if 1 in payload:
                z1 = payload.get(1)

        if w1 < w:
            w = w1
        if x1 < x:
            x = x1
        if y1 < y:
            y = y1
        if z1 < z:
            z = z1
        self.rt_tbl_D.clear()
        self.rt_tbl_D[0] = {0:w,1:x}
        self.rt_tbl_D[1] = {0: y, 1:z}


    # This sends the current router's routing table --> self, to an interface i
    # Todo: IF THERE'S TIME Check to make sure routing table is accurate based on links from the LinkLayer, and costs from the router.intf_cost_ list
    # right now the correct links are hard coded into the routing tables
    #  @param i Interface number on which to send out a routing update

    def send_routes(self, i):
        

        packet_message = UpdateMessage(self.rt_tbl_D)
        message_S = packet_message.to_byte_S()

        p = NetworkPacket(self.name, 0, 'control', message_S)
        try:
            # TODO: Add logic to send out a route update
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    # Print routing table
    def print_routes(self):
        # DoneTODO: print the routes as a two dimensional table for easy inspection

        # df = pd.DataFrame.from_dict(self.rt_tbl_D, orient='columns', dtype=int)
        
        w, x, y, z = '~','~','~','~'
        df = self.rt_tbl_D
        print (df)

        if 0 in df:
            temp = df.get(0)
            if 0 in temp:
                w = temp.get(0)
            if 1 in temp:
                x = temp.get(1)
            print (temp)
        if 1 in df:
            temp = df.get(1)
            if 0 in temp:
                y = temp.get(0)
            if 1 in temp:
                z = temp.get(1)
        # print (df)
        # temp = df.get(0)
        # temp2 = df.get(1)
        # print (temp)
        # print (temp2)
        #need to change this eventually
        # if 1 in df:         
        #     w = temp.get(1)
        # if 2 in df:
        #     z = temp2.get(1)




        print('\n'+'%s: routing table:' % self)
        print ('Cost to: 1 2')
        print ('        -----')
        print ('From: 0| %s %s' % (w,x))
        print ('      1| %s %s' % (y,z))

    # thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return

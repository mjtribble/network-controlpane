"""
Created on Oct 12, 2016

@author: mwitt_000
"""
import network_1
import link_1
import threading
from time import sleep
import sys

# configuration parameters
router_queue_size = 0  # 0 means unlimited
simulation_time = 1  # give the network_1 sufficient time to transfer all packets before quitting
max = sys.maxsize

if __name__ == '__main__':
    object_L = []  # keeps track of objects, so we can kill their threads

    # create network hosts
    host_1 = network_1.Host(1)
    object_L.append(host_1)
    host_2 = network_1.Host(2)
    object_L.append(host_2)

    # create routers and routing tables for connected clients (subnets)
    # ROUTER A
    router_a_rt_tbl_D = {1: {0: max, 1: 1},  # from routerA to host1 through interface 1 for cost 1
                         2: {0: 1, 1: max}}  # from routerA to host2 through interface 0 and cost of 1
    router_a = network_1.Router(name='A',
                                intf_cost_L=[1, 1],
                                rt_tbl_D=router_a_rt_tbl_D,
                                max_queue_size=router_queue_size)
    object_L.append(router_a)

    # ROUTER B
    router_b_rt_tbl_D = {2: {0: 3, 1: max},  # routerB to host 2 through interface 0 for cost 3
                         1: {0: max, 1: 1}}  # routerB to host 1 through interface 1 for cost 1
    router_b = network_1.Router(name='B',
                                intf_cost_L=[1, 3],
                                rt_tbl_D=router_b_rt_tbl_D,
                                max_queue_size=router_queue_size)
    object_L.append(router_b)

    # create a link_1 Layer to keep track of links between network_1 nodes
    link_layer = link_1.LinkLayer()
    object_L.append(link_layer)

    # send links
    link_layer.add_link(link_1.Link(host_1, 0, router_a, 0))
    link_layer.add_link(link_1.Link(router_a, 0, router_b, 0))
    link_layer.add_link(link_1.Link(router_b, 0, host_2, 0))

    # return links
    link_layer.add_link(link_1.Link(host_2, 0, router_b, 1))
    link_layer.add_link(link_1.Link(router_b, 1, router_a, 1))
    link_layer.add_link(link_1.Link(router_a, 1, host_1, 0))

    # start all the objects
    thread_L = []
    for obj in object_L:
        thread_L.append(threading.Thread(name=obj.__str__(), target=obj.run))

    for t in thread_L:
        t.start()

    # send out routing information from router A to router B interface 0
    router_a.send_routes(0)

    # create some send events
    for i in range(1):
        host_1.udt_send(2, 'Sample host_1 data %d' % i)

    # give the network_1 sufficient time to transfer all packets before quitting
    sleep(simulation_time)

    # print the final routing tables
    for obj in object_L:
        if str(type(obj)) == "<class 'network_1.Router'>":
            obj.print_routes()

    # join all threads
    for o in object_L:
        o.stop = True
    for t in thread_L:
        t.join()

    print("All simulation threads joined")

    # writes to host periodically

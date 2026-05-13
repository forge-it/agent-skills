Okay, 
Input type 1: I will give you some commit messages with ticket numbers in them and example of a work log. Output: you will give me a work log.
Input type 2: I will give you a ticket number that I have investigated and made a report for it and you should extract a short work log. Output: you will give me a work log.

Steps input type 1:
- group related commit messages for the same target ticket
* take a group of commit message
* extract ticket number from the commit messages 
* read ticket from jira (you have access)
* understand commit messages for that specific ticket
* make that a work log for that ticket
* repeat for the next group

Steps input type 2:
- read the give ticket that I investigated
* read commend for my input on invastigation
* create the work log
* repeat for the next investigated ticket

Rules: 
* make the "Details" section less technical
* focus more on what was achieved and less on technical stuff
* bold only the ticket number from the work log

---
Example work log:
SYN-1838
* Ticket title: Deploy a K8s cluster PoC using kubean
* Done by: me
* Type: technical task
* Category: development
* Status: in progress
* Summary: Implemented the automated VM provisioning flow that Vulcan uses to create virtual machines across all datacenter nodes when a Kubernetes cluster is requested in the context of poc
* Details: Built the layer that lets Vulcan automatically create one virtual machine on every node in the datacenter when a new Kubernetes cluster is requested. Added upfront checks that reject invalid requests early — such as not enough nodes for high availability or conflicting IP addresses. The provisioning runs as a background job, reports progress, and returns the assigned IPs of all created VMs once they boot. Covered the new functionality with 85 unit tests.

---
Observations:
* the commits can be given for different or various days, group them by day like in the example below
* input type 1 with input type 2 can be combined in the same prompt
* when there is a commit message saying that I "Cristian Ciortea" merged a branch, that means I made a code review for that ticket

Example:
13.03.2026
SYN-1838
* Ticket title:  ...
SYN-1839
* Ticket title: ...

16.03.2026
SYN-1841
* Ticket title:  ...
---

My commits & tickets are: [will be given below]
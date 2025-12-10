# Weather Watcher Software

## Description
This project aims at creating an application which logs climate details captured by ESP32 Microcomputers with sensors.

## Resources and Technologies

ESP32 Microcontrollers with climate sensors for measuring climate details:
- temperature
- humidity
- oxygen concentration
- light intensity
- CaaS (Container as a Service) with one Container for each Service
  - Telekom Open Cloud Server and Git for deployment
  - Java Spring
  - Micropython
  - Postgres
  - Grafana

Architecture:

This project will work in a container structure (probably Docker or Kubernetes) There will be 3 containers running serverside which are:

1. Frontend Webserver (probably implementing a Grafana Dashboard)
2. Backend Webserver (REST API with Spring)
3. Database (Postgres)

![component flowchart](Documentation/images/weatherwatcher1.png) 

And one Micro Python Webserver on each ESP32.

![component flowchart](Documentation/images/circuit.png) 


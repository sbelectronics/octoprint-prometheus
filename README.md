# Prometheus Client for OctoPrint #
Scott Baker, http://www.smbaker.com/

## Purpose ##

This plugin implements a Prometheus client inside of OctoPrint. This is native endpoint served up directly from the OctoPrint. This allows you to monitor your 3D printer using the combination of Prometheus and Grafana.

This plugin will export the following data:
* Progress
* Heat bed temperature
* Tool (extruder) temperatures
* X, Y, Z, E coordinates

It will also monitor several built in prometheus python client variables, such as process start time, cpu seconds, virtual memory, open file descriptors, etc.

The reason I chose to do this is I already have Prometheus/Grafana for monitoring the environment in my office. Having OctoPrint data available lets me keep track of printer utilization using the same toolchain, and to correlate printer usage with environmental changes.

## Dependencies ##

This package depends upon `prometheus_client`, which should be automatically installed as necessary by pip. 

## Installation ##

Either of the following commands can be used to install the package from the command line:

* `pip install octoprint-prometheus`
* `pip install https://github.com/sbelectronics/octoprint-prometheus/archive/master.zip`

Additionally, you can install this using the Octoprint GUI by using Plugin Manager --> Get More --> from URL, and entering the URL `https://github.com/sbelectronics/octoprint-prometheus/archive/master.zip`.

## Configuration ##

The printer by default exposes an endpoint on port 8000. This port may be changed using the plugin's setup page in the OctoPrint UI.

## Installing Prometheus and Grafana ##

Personally I install it using helm and kubernetes, but there are many different ways to install these tools. Using the helm chart, I add a datasource to Prometheus as follows:

```yaml
      scrape_configs:
        # 3dprinter
        - job_name: '3dprinter'
          metrics_path: /metrics
          scrape_interval: 10s
          static_configs:
            - targets:
              - 198.0.0.246:8000
```

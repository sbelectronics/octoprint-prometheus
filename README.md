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

## Testing ##

You can use `curl` or a web browser to view the Prometheus endpoint and ensure it is producting data. For example, 

```bash
pi@octopi:~ $ curl http://localhost:8000/
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="2",minor="7",patchlevel="13",version="2.7.13"} 1.0
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 3.17431808e+08
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 8.835072e+07
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 1.55090426429e+09
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 54.35
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 38.0
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 1024.0
# HELP temperature_bed_target temperature_bed_target
# TYPE temperature_bed_target gauge
temperature_bed_target 0.0
# HELP temperature_tool0_actual temperature_tool0_actual
# TYPE temperature_tool0_actual gauge
temperature_tool0_actual 21.3
# HELP temperature_bed_actual temperature_bed_actual
# TYPE temperature_bed_actual gauge
temperature_bed_actual 20.9
# HELP temperature_tool0_target temperature_tool0_target
# TYPE temperature_tool0_target gauge
temperature_tool0_target 0.0
```

Note that certain fields will not appear until you've connected to your printer. 

## Installing Prometheus and Grafana ##

Install Prometheus and Grafana on another machine or another pi, as you'll be maintaining a database.

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

How to install Prometheus and Grafana is beyond the scope of this README. The following links may be helpful to you:

* https://medium.com/@at_ishikawa/install-prometheus-and-grafana-by-helm-9784c73a3e97
* https://www.digitalocean.com/community/tutorials/how-to-install-prometheus-on-ubuntu-16-04
* http://docs.grafana.org/installation/debian/
* https://github.com/carlosedp/arm-monitoring

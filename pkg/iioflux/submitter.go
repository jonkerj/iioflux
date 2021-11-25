package iioflux

import (
	"context"
	"fmt"
	"sync"
	"time"

	influxdb2 "github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/domain"
	"github.com/jonkerj/goiio"
	log "github.com/sirupsen/logrus"
)

func NewSubmitter(c *Config, idbConfig *InfluxDBConfig, interval string) (*Submitter, error) {
	submitter := &Submitter{Config: c, hosts: make(map[string]*IIOClient)}
	for _, host := range c.Hosts {
		client, err := goiio.New(host.Remote)
		if err != nil {
			return nil, fmt.Errorf("error client client for %s: %v", host.Name, err)
		}

		submitter.hosts[host.Name] = &IIOClient{Client: client, Devices: host.Devices}
	}

	submitter.influxDBClient = influxdb2.NewClient(idbConfig.URL, idbConfig.Token)
	health, err := submitter.influxDBClient.Health(context.TODO())
	if err != nil {
		return nil, fmt.Errorf("influxdb client returned an error: %v", err)
	}

	if health.Status != domain.HealthCheckStatusPass {
		return nil, fmt.Errorf("influxdb server was not healthy, status=%v", health.Status)
	}

	log.Infof("connected with InfluxDB version %s", *health.Version)

	submitter.influxWriteAPI = submitter.influxDBClient.WriteAPI(idbConfig.Org, idbConfig.Bucket)

	d, err := time.ParseDuration(interval)
	if err != nil {
		return nil, fmt.Errorf("error parsing interval: %v", err)
	}
	submitter.interval = d

	return submitter, nil
}

func (s *Submitter) poll() {
	var wg sync.WaitGroup
	log.Debug("entering poll function")

	for host, client := range s.hosts {
		wg.Add(1)

		log.Debugf("working on host %s", host)
		go func(host string, client *IIOClient) {
			defer wg.Done()

			client.Client.FetchAttributes()

			for _, device := range client.Devices {
				d := client.Client.Context.GetDeviceByNameOrID(device.Match.Name, device.Match.ID)
				if d == nil {
					log.Warnf("could not find device %s at host %s", device.Name, host)
					continue
				}

				p := influxdb2.NewPointWithMeasurement(device.Name).AddTag("host", host)
				for _, c := range d.Channels {
					v := c.GetValue()
					log.Infof("%s/%s/%s: %0.2f", host, device.Name, c.ID, v)
					p = p.AddField(c.ID, v)
				}
				if len(p.FieldList()) == 0 {
					log.Warnf("device %s yielded zero attributes", device.Name)
					continue
				}
				s.influxWriteAPI.WritePoint(p)
			}
		}(host, client)
	}
	wg.Wait()
}

func (s *Submitter) Run() {
	log.Infof("going to poll every %v", s.interval)
	ticker := time.NewTicker(s.interval)
	for ; true; <-ticker.C {
		s.poll()
	}
}

func (s *Submitter) Shutdown() {
	s.influxDBClient.Close()
}

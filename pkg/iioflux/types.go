package iioflux

import (
	"time"

	influxdb2 "github.com/influxdata/influxdb-client-go/v2"
	"github.com/influxdata/influxdb-client-go/v2/api"
	"github.com/jonkerj/goiio"
)

type Config struct {
	Hosts []*Host `yaml:"hosts"`
}

type Host struct {
	Name    string    `yaml:"name"`
	Remote  string    `yaml:"remote"`
	Devices []*Device `yaml:"devices"`
}

type Device struct {
	Name  string `yaml:"name"`
	Match *Match `yaml:"match"`
}

type Match struct {
	Name *string `yaml:"name,omitempty"`
	ID   *string `yaml:"id,omitempty"`
}

type IIOClient struct {
	Devices []*Device
	Client  *goiio.IIO
}

type Submitter struct {
	Config         *Config
	hosts          map[string]*IIOClient
	influxDBClient influxdb2.Client
	influxWriteAPI api.WriteAPI
	interval       time.Duration
}

type InfluxDBConfig struct {
	URL    string
	Token  string
	Org    string
	Bucket string
}

package cmd

import (
	"fmt"

	"github.com/jonkerj/iioflux/pkg/iioflux"
	log "github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	rootCmd = &cobra.Command{
		Use:   "iioflux",
		Short: "submit iiod measurements into influxdb",
		Run:   root,
	}
)

func init() {
	viper.AutomaticEnv()
	viper.SetEnvPrefix("iioflux")
	flags := rootCmd.PersistentFlags()
	flags.String("sensors", "config.yaml", "YAML file containing the remote config")
	flags.String("interval", "1m", "Interval between polls, expressed as golang duration")
	flags.String("loglevel", "info", "Log level")
	flags.String("influxdb_org", "", "InfluxDB Organization")
	flags.String("influxdb_url", "http://influxdb.influxdb:8086", "InfluxDB URL")
	flags.String("influxdb_token", "notme:notmypassword", "InfluxDB token")
	flags.String("influxdb_bucket", "iioflux/autogen", "InfluxDB bucket")
	viper.BindPFlags(flags)
}

func root(cmd *cobra.Command, args []string) {
	sensors, err := iioflux.LoadConfig(viper.GetString("sensors"))
	if err != nil {
		panic(err)
	}

	idbConfig := &iioflux.InfluxDBConfig{
		URL:    viper.GetString("influxdb_url"),
		Token:  viper.GetString("influxdb_token"),
		Bucket: viper.GetString("influxdb_bucket"),
		Org:    viper.GetString("influxdb_org"),
	}

	level, err := log.ParseLevel(viper.GetString("loglevel"))
	if err != nil {
		panic(fmt.Errorf("error parsing loglevel: %v", err))
	}
	log.Infof("setting log level to %v", level)
	log.SetLevel(level)

	submitter, err := iioflux.NewSubmitter(sensors, idbConfig, viper.GetString("interval"))
	if err != nil {
		panic(err)
	}
	defer submitter.Shutdown()
	submitter.Run()
}

func Execute() {
	rootCmd.Execute()
}

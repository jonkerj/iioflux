package iioflux

import (
	"fmt"
	"io/ioutil"

	yaml "sigs.k8s.io/yaml"
)

func LoadConfig(filename string) (*Config, error) {
	var c Config

	yamlBytes, err := ioutil.ReadFile(filename)
	if err != nil {
		return nil, fmt.Errorf("error loading '%s': %v", filename, err)
	}

	if err = yaml.Unmarshal(yamlBytes, &c); err != nil {
		return nil, fmt.Errorf("error unmarshalling YAML: %v", err)
	}

	return &c, nil
}

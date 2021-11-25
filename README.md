# IIOFlux
An IIO-to-InfluxDB submitter for Kubernetes, written in Go

## Usage
```
$ kubectl create ns iioflux
$ kubectl -n iioflux create configmap config --from-file=config.yaml
$ kubectl -n iioflux create secret generic influxdb-creds \
    --from-literal=IIOFLUX_INFLUXDB_TOKEN=foo:w00haah
$ kubectl apply -n iioflux -f k8s-deployment.yaml
```

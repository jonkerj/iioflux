# IIOFlux
An IIO-to-InfluxDB submitter for Kubernetes, written in Python

## Usage
```
$ kubectl create ns iioflux
$ kubectl -n iioflux create configmap config --from-file=config.yaml
$ kubectl -n iioflux create secret generic secrets \
    --from-literal=influxdb.connection.username=foo \
    --from-literal=influxdb.connection.password=w00haah
$ kubectl apply -f k8s-deployment.yaml
```
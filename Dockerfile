FROM golang:1.17 as builder
COPY . .
RUN CGO_ENABLED=0 go build -o /app main.go

FROM scratch
COPY --from=builder /app /app
ENTRYPOINT ["/app"]
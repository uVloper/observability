FROM grafana/tempo:2.7.1
COPY tempo.yaml /etc/tempo.yaml
ENTRYPOINT ["/tempo"]
CMD ["-config.file=/etc/tempo.yaml"]

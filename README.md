# InfiniBand Operator

This operator charm installs and removes the Mellanox InfiniBand drivers
on a machine when the `juju-info` integration is created with a principle charm.

# Example Usage
```bash
juju deploy slurmd --series centos7
juju deploy infiniband --channel edge

juju integrate slurmd infiniband
```

### Copyright
* Omnivector, LLC &copy; <admin@omnivector.solutions>

### License
* Apache v2 - see [LICENSE](./LICENSE)

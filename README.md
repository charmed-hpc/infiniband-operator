# InfiniBand Operator

This operator charm installs and removes the Mellanox InfiniBand drivers
on a machine when the `juju-info` integration is created with a principle charm.

# Example Usage

Build the charm

```bash
cd infiniband-operator
charmcraft pack
mv infiniband_ubuntu-20.04-amd64_ubuntu-22.04-amd64_centos-7-amd64.charm infiniband.charm
```
Deploy the charm

```bash
juju deploy slurmd --series centos7
juju deploy ./infiniband.charm

juju integrate slurmd infiniband
```

### Copyright
* Omnivector, LLC &copy; <admin@omnivector.solutions>

### License
* Apache v2 - see [LICENSE](./LICENSE)

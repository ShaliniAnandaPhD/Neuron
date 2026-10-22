# Neuron Sandbox

The sandbox's guided builder (`guided_neuron_builder`) was a compiled macOS
(Apple Silicon) executable with no source in this repository. Binaries don't
belong in git history or diffs, so it was removed from the working tree in
October 2026. To get it back:

```bash
git show f2fab9a:sandbox/guided_neuron_builder > guided_neuron_builder
chmod +x guided_neuron_builder
```

To keep distributing it, attach it to a GitHub Release instead.

Access to the sandbox materials is governed by
[`sandbox-notice.md`](sandbox-notice.md).

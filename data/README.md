# Data layout

The local server dataset is expected at:

```text
data/raw/spatiallab_mcq.json
/root/autodl-fs/img/<Image_Filename>
```

The local JSON copy contains 1,400 records and is ignored by Git. The 1,400
images remain on the experiment server and are not duplicated into this
repository. `manifest.json` records the expected record count and checksum.

Before publishing any benchmark JSON or images, verify the redistribution
terms of the original SpatialLab release. The code itself only requires these
fields:

- `id`
- `Image_Filename`
- `Question`
- `Option_1` ... `Option_4`
- `Answer`

`Category` and `Sub_Category` are retained for post-hoc reporting and for the
explicit `oracle` upper-bound configuration. They are not passed to the
automatic router or the main pipeline.

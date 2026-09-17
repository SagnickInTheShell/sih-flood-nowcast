# Judge Q&A -- Prepared Honest Answers

**Q: Is the GNN a replacement for a real hydraulic simulator (e.g. SWMM)?**
A: No -- it's a surrogate trained to approximate hydraulic behaviour for
speed. For nowcasting, a full numerical solve is too slow; the GNN gives
near-real-time output. It should be periodically validated against a proper
hydraulic model or ground truth before operational use.

**Q: Where does your training data come from?**
A: For the prototype: a simplified physics-based routing baseline over
synthetic/OSM-derived terrain. Real deployment needs historical flood-depth
records or sensor data from the municipal body -- not currently available.

**Q: What accuracy does your model achieve?**
A: We report MAE/RMSE against our own physics baseline, not against observed
real-world flooding, because we don't have access to verified ground truth
yet. We're explicit about this everywhere in the product.

**Q: How reliable is OSM drainage data for a real Indian city ward?**
A: Inconsistent/incomplete in most Indian cities -- a real limitation. For a
real deployment we'd manually curate/digitize the target ward's drainage
network.

**Q: What's the latency for real-time deployment?**
A: Depends on nowcast refresh rate and GNN inference time; inference itself
is designed to be seconds-scale. End-to-end pipeline latency with a live feed
is unverified pending a real deployment.

**Q: Why a GCN and not a more sophisticated GNN architecture?**
A: 3x GCNConv (hidden=64) was chosen as a simple, fast-training baseline
surrogate appropriate for a ~50-node prototype graph and a hackathon
timeline. `app/ml/model.py` documents where it approximates (edge features
are combined into a single scalar weight because vanilla GCNConv doesn't
accept multi-dimensional edge attributes) -- a richer conv (e.g. NNConv,
GAT with edge features) is a natural next step at a larger scale.

**Q: What happens if I point this at a real ward tomorrow?**
A: `PILOT_MODE=real` + `REAL_WARD_BBOX` switches data sourcing to OSM +
SRTM with zero changes to the hydrology/ML/routing pipeline (see
`docs/ARCHITECTURE.md`'s synthetic/real boundary). It still needs: a
downloaded DEM tile (`scripts/download_srtm.py`), and ideally curated
drainage/land-use data before results are trustworthy -- see
`docs/DATA_SOURCES.md`.

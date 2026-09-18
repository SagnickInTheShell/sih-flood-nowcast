// ASSUMPTION: the real-mode label names Bellandur specifically since that's
// the only real bbox this project currently ships/documents (see
// docs/DATA_SOURCES.md). A future multi-ward deployment would want the
// backend to return a ward display name rather than hardcoding it here.
export default function SyntheticDataBadge({ isSynthetic }: { isSynthetic: boolean }) {
  if (!isSynthetic) {
    return (
      <span
        className="text-xs px-2 py-1 rounded bg-safeGreen/20 text-safeGreen border border-safeGreen"
        title="Real road network (OpenStreetMap) and real elevation data for Bellandur, Bengaluru."
      >
        Bellandur, Bengaluru &mdash; Live OSM/SRTM Data
      </span>
    );
  }
  return (
    <span
      className="text-xs px-2 py-1 rounded bg-gold/20 text-gold border border-gold"
      title="This ward is a deterministic synthetic reference ward, not a real place."
    >
      Synthetic Reference Ward
    </span>
  );
}

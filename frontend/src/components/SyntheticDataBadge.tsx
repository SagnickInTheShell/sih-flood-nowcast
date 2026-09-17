export default function SyntheticDataBadge({ isSynthetic }: { isSynthetic: boolean }) {
  if (!isSynthetic) {
    return (
      <span className="text-xs px-2 py-1 rounded bg-safeGreen/20 text-safeGreen border border-safeGreen">
        Live Data
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

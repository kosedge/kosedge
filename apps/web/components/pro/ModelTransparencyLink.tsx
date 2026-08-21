import Link from "next/link";
import {
  MODEL_TRANSPARENCY_HREF,
  MODEL_TRANSPARENCY_TITLE,
} from "@/lib/model-transparency-hub";

/** Quiet text link — boards stay clean; the hub owns the essay. */
export default function ModelTransparencyLink({
  className = "text-xs text-kos-text/45 hover:text-kos-gold",
  label = "Model transparency",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <Link
      href={MODEL_TRANSPARENCY_HREF}
      className={className}
      title={MODEL_TRANSPARENCY_TITLE}
    >
      {label}
    </Link>
  );
}

import { cn } from "@/lib/utils";

/**
 * Skeleton loading placeholder.
 * Renders an animated pulse block to indicate loading state.
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-primary/10", className)}
      {...props}
    />
  );
}

export { Skeleton };

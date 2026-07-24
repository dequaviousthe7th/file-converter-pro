import type { ButtonHTMLAttributes } from "react";
import { cn } from "../lib/utils";

type Variant = "primary" | "outline" | "ghost" | "danger";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-accent text-[#08110e] font-semibold hover:bg-accent-hover active:bg-accent shadow-[0_0_20px_rgba(0,212,170,0.18)] disabled:shadow-none",
  outline:
    "border border-hairline-strong text-ink hover:border-white/25 hover:bg-white/[0.04]",
  ghost: "text-ink-dim hover:bg-white/[0.06] hover:text-ink",
  danger: "text-danger hover:bg-danger-soft",
};

const SIZES: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-9 px-4 text-[13px] gap-2",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export default function Button({
  variant = "ghost",
  size = "md",
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex select-none items-center justify-center whitespace-nowrap rounded-ctl transition-colors duration-100 disabled:pointer-events-none disabled:opacity-40",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  );
}

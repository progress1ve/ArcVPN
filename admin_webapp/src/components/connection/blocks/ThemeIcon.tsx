import type { ColorGradientStyle } from '@/utils/colorParser';

interface ThemeIconProps {
  getSvgHtml: (key: string | undefined) => string;
  svgIconKey?: string;
  gradientStyle: ColorGradientStyle;
  isMobile: boolean;
}

export function ThemeIcon({ getSvgHtml, svgIconKey, gradientStyle, isMobile }: ThemeIconProps) {
  const svgHtml = getSvgHtml(svgIconKey);
  if (!svgHtml) return null;
  const size = isMobile ? 36 : 44;
  const iconSize = isMobile ? 18 : 22;

  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full"
      style={{
        width: size,
        height: size,
        background: gradientStyle.background,
        border: gradientStyle.border,
        boxShadow: gradientStyle.boxShadow,
      }}
    >
      <div
        style={{ width: iconSize, height: iconSize }}
        className="[&>svg]:h-full [&>svg]:w-full"
        dangerouslySetInnerHTML={{ __html: svgHtml }}
      />
    </div>
  );
}

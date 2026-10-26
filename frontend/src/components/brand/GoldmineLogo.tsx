type GoldmineLogoProps = {
  size?: 'small' | 'medium' | 'large';
  className?: string;
};

const sizeClasses = {
  small: 'h-7 w-7 rounded-lg',
  medium: 'h-9 w-9 rounded-xl',
  large: 'h-20 w-20 rounded-[1.4rem]',
};

export default function GoldmineLogo({ size = 'medium', className = '' }: GoldmineLogoProps) {
  return (
    <img
      src="/goldmine-logo.png"
      alt=""
      aria-hidden="true"
      className={`shrink-0 object-cover ${sizeClasses[size]} ${className}`}
    />
  );
}

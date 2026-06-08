import * as React from "react";

/**
 * Breakpoint in pixels under which the screen is classified as mobile.
 * Matches typical TailwindCSS/shadcn breakpoints (768px for md).
 */
const MOBILE_BREAKPOINT = 768;

/**
 * Custom React hook that detects whether the current viewport is mobile-sized.
 * Uses window.matchMedia to listen to viewport resize events reactively,
 * preventing hydration mismatches by initializing as undefined and updating on mount.
 *
 * @returns {boolean} True if the screen width is less than the MOBILE_BREAKPOINT (768px).
 */
export function useIsMobile() {
	const [isMobile, setIsMobile] = React.useState<boolean | undefined>(
		undefined,
	);

	React.useEffect(() => {
		const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
		const onChange = () => {
			setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
		};
		mql.addEventListener("change", onChange);
		setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
		return () => mql.removeEventListener("change", onChange);
	}, []);

	return !!isMobile;
}

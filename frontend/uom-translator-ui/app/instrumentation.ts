import { registerOTel } from "@vercel/otel";

export function register() {
	registerOTel({ serviceName: "uom-translator-ui" });
}

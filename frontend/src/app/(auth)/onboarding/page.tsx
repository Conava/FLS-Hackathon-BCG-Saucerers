/**
 * Onboarding page — server component frame.
 * Renders the client-side OnboardingStepper.
 * No tab bar (handled by the auth layout).
 */
import { OnboardingStepper } from "./stepper";

export default function OnboardingPage() {
  return <OnboardingStepper />;
}

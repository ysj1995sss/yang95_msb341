import { Volume2, VolumeX } from "lucide-react";
import { useEffect, useState } from "react";

const supported = () => typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;

/** Reads the question out loud with the device's own voice. Hidden where the browser has none. */
export function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);

  // A new question, or leaving the page, stops whatever is being read.
  useEffect(() => {
    setSpeaking(false);
    return () => { if (supported()) window.speechSynthesis.cancel(); };
  }, [text]);

  if (!supported()) return null;

  function toggle() {
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.cancel();
    synth.speak(utterance);
    setSpeaking(true);
  }

  return (
    <button type="button" data-speak aria-pressed={speaking} aria-label={speaking ? "Stop reading aloud" : "Read aloud"}
      onClick={toggle}
      className={`inline-flex size-12 shrink-0 cursor-pointer items-center justify-center rounded-full transition ${
        speaking ? "bg-plum-100 text-plum-700 dark:text-onplum-soft" : "text-muted hover:bg-sand hover:text-ink"}`}>
      {speaking ? <VolumeX aria-hidden className="size-6" /> : <Volume2 aria-hidden className="size-6" />}
    </button>
  );
}

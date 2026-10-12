"use client";

import { VideoTrack, useTracks } from "@livekit/components-react";
import { Track } from "livekit-client";

/** The employee's published video inside a <LiveKitRoom>: webcam and/or screen share. Never audio (no microphone). */
export function LiveFeeds({ compact }: { compact?: boolean }) {
  const tracks = useTracks([Track.Source.Camera, Track.Source.ScreenShare], { onlySubscribed: true });
  const camera = tracks.find((t) => t.source === Track.Source.Camera);
  const screen = tracks.find((t) => t.source === Track.Source.ScreenShare);
  if (!camera && !screen) return <div className="video-stage"><span className="small">Connecting…</span></div>;
  if (compact) {
    // Grid tile: the webcam fills the tile; the screen shows when there is no webcam, or as a small inset.
    const main = camera ?? screen!;
    return (
      <div className="video-stage" style={{ position: "relative" }}>
        <VideoTrack trackRef={main} />
        {camera && screen && <div className="video-inset"><VideoTrack trackRef={screen} /></div>}
      </div>
    );
  }
  return (
    <div className={camera && screen ? "grid grid-2" : ""}>
      {camera && <div className="stack-sm"><span className="muted small">Webcam</span><div className="video-stage"><VideoTrack trackRef={camera} /></div></div>}
      {screen && <div className="stack-sm"><span className="muted small">Screen</span><div className="video-stage"><VideoTrack trackRef={screen} /></div></div>}
    </div>
  );
}

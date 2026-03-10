"use client";

import { Canvas } from "@react-three/fiber";
import DataScene from "./DataScene";
import CameraRig from "./CameraRig";

export default function SceneWrapper() {
  return (
    <div className="fixed inset-0 z-0 bg-gradient-to-b from-[#000000] to-[#0a0a0a]">
      <Canvas camera={{ position: [0, 0, 10], fov: 60 }}>
        <ambientLight intensity={0.5} />
        <DataScene />
        <CameraRig />
      </Canvas>
    </div>
  );
}

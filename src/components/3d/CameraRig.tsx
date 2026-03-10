"use client";

import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export default function CameraRig() {
    useFrame((state, delta) => {
        // Subtle mouse tracking. Pointer is -1 to 1.
        const targetX = state.pointer.x * 2;
        const targetY = state.pointer.y * 2;

        // Smoothly interpolate camera position based on mouse position
        state.camera.position.x = THREE.MathUtils.lerp(
            state.camera.position.x,
            targetX,
            delta * 2
        );
        state.camera.position.y = THREE.MathUtils.lerp(
            state.camera.position.y,
            targetY,
            delta * 2
        );

        // Keep the camera looking at the center
        state.camera.lookAt(0, 0, 0);
    });

    return null;
}

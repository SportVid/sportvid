import * as PIXI from "pixi.js";

import { Timeline } from "./timeline";
// import * as tf from '@tensorflow/tfjs';
import { resampleApprox, getMax, getMin } from "./utils";

export class ScalarLineTimeline extends Timeline {
  constructor({
    timelineId,
    width = 10,
    height = 10,
    startTime = 0,
    endTime = 10,
    duration = 10,
    data = null,
    fill = 0xffffff,
    renderer = null,
    resolution = 1024,
    oversampling = 1,
  }) {
    super({ timelineId, width, height, startTime, endTime, duration, fill });

    this.pData = data;

    this.pDataMinTime = getMin(data.time);
    this.pDataMaxTime = getMax(data.time);

    this.pResolution = resolution;
    this.pOversampling = oversampling;
    this.pRenderer = renderer;

    this.path = this.renderGraph();

    // this.path.y = this.pHeight / 2;

    this.addChild(this.path);

    this.scaleContainer();
  }

  // renderGraph() {
  //   const renderWidth = this.pResolution;
  //   const r = renderWidth / this.pDuration;

  //   const rt = new PIXI.RenderTexture({
  //     width: renderWidth,
  //     height: this.pHeight,
  //     // PIXI.SCALE_MODES.NEAREST,
  //     scaleMode: PIXI.linear,

  //     resolution: 1,
  //   });

  //   const sprite = new PIXI.Sprite(rt);

  //   const path = new PIXI.Graphics().setStrokeStyle(1, 0xae1313, 1);

  //   const targetSize = this.pOversampling * this.pResolution;
  //   const y = resampleApprox({ data: this.pData.y, targetSize: targetSize });
  //   const times = resampleApprox({ data: this.pData.time, targetSize: targetSize });

  //   (this.pData.delta_time * this.pData.time.length) / times.length;
  //   times.forEach((t, i) => {
  //     if (i == 0) {
  //       path.moveTo(r * t, this.pHeight - y[i] * this.pHeight);
  //     }
  //     path.lineTo(r * t, this.pHeight - y[i] * this.pHeight);
  //   });

  //   this.pRenderer.render({
  //     container: path,
  //     target: rt,
  //   });
  //   return sprite;
  // }

  renderGraph() {
    if (!this.pRenderer) {
      console.error("Renderer is not initialized");
      return null;
    }

    const renderWidth = this.pResolution;
    const r = renderWidth / this.pDuration;

    const rt = new PIXI.RenderTexture({
      width: renderWidth,
      height: this.pHeight,
      scaleMode: PIXI.SCALE_MODES.LINEAR,
      resolution: 1,
    });

    const sprite = new PIXI.Sprite(rt);

    // Create graphics with new stroke style syntax
    const path = new PIXI.Graphics().lineStyle({
      width: 1,
      color: 0xae1313,
      alpha: 1,
    });

    const targetSize = this.pOversampling * this.pResolution;
    const y = resampleApprox({ data: this.pData.y, targetSize: targetSize });
    const times = resampleApprox({ data: this.pData.time, targetSize: targetSize });

    // Start the path
    path.moveTo(0, this.pHeight - y[0] * this.pHeight);

    // Draw the line
    times.forEach((t, i) => {
      path.lineTo(r * t, this.pHeight - y[i] * this.pHeight);
    });

    try {
      this.pRenderer.render({
        container: path,
        target: rt,
      });
    } catch (error) {
      console.error("Error rendering timeline:", error);
      return null;
    }

    // Make sure sprite is visible and positioned correctly
    sprite.visible = true;
    sprite.x = 0;
    sprite.y = 0;
    sprite.width = renderWidth;
    sprite.height = this.pHeight;

    return sprite;
  }

  scaleContainer() {
    if (this.path && this.path.visible) {
      const width = this.timeToX(this.pDuration) - this.timeToX(0);
      const x = this.timeToX(0);
      this.path.x = x;
      this.path.width = width;

      // Force update of transform
      this.path.updateTransform();
    }
  }
}

// scaleContainer() {
//   if (this.path) {
//     const width = this.timeToX(this.pDuration) - this.timeToX(0);
//     const x = this.timeToX(0);
//     this.path.x = x;
//     this.path.width = width;
//   }
// }

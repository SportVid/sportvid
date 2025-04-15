import * as PIXI from "pixi.js";

import { Timeline } from "./timeline";
import { resampleApprox } from "./utils";

export class ColorTimeline extends Timeline {
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

    this.pDataMinTime = Math.min(...data.time);
    this.pDataMaxTime = Math.max(...data.time);

    this.pResolution = resolution;
    this.pOversampling = oversampling;
    this.pRenderer = renderer;

    this.cRects = this.renderGraph();

    this.addChild(this.cRects);

    this.scaleContainer();
  }

  renderGraph() {
    const renderWidth = this.pResolution;
    const r = renderWidth / this.pDuration;

    const rt = new PIXI.RenderTexture({
      width: renderWidth,
      height: this.pHeight,
      // PIXI.SCALE_MODES.NEAREST,
      scaleMode: PIXI.linear,

      resolution: 1,
    });

    const sprite = new PIXI.Sprite(rt);

    let colorRects = new PIXI.Graphics();

    const targetSize = this.pOversampling * this.pResolution;
    const colors = resampleApprox({
      data: this.pData.colors,
      targetSize: targetSize,
    });
    const times = resampleApprox({
      data: this.pData.time,
      targetSize: targetSize,
    });
    const deltaTime = (this.pData.delta_time * this.pData.time.length) / times.length;
    times.forEach((t, i) => {
      const rgb = colors[i];
      const color = (rgb[0] << 16) + (rgb[1] << 8) + rgb[2];

      colorRects.rect(Math.max(0, r * (t - deltaTime / 2)), 0, r * deltaTime, this.pHeight);
      colorRects.fill(color);
    });

    this.pRenderer.render({
      container: colorRects,
      target: rt,
    });
    return sprite;
  }

  scaleContainer() {
    const targetSize = this.pOversampling * this.pResolution;

    const times = resampleApprox({
      data: this.pData.time,
      targetSize: targetSize,
    });

    const deltaTime = (this.pData.delta_time * this.pData.time.length) / times.length;

    if (this.cRects) {
      const width =
        this.timeToX(this.pData.time[this.pData.time.length - 1] + deltaTime / 2) -
        this.timeToX(this.pData.time[0]);
      const x = this.timeToX(this.pData.time[0]);
      this.cRects.x = x;
      this.cRects.width = width;
    }
  }
}

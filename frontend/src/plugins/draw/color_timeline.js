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

    this.pTimelineId = timelineId;
    this.pData = data;
    this.pHeight = height;
    this.pWidth = width;
    this.pStartTime = startTime;
    this.pEndTime = endTime;
    this.pDuration = duration;
    this.pFill = fill;

    this.pDataMinTime = Math.min(...this.pData.time);
    this.pDataMaxTime = Math.max(...this.pData.time);

    this.pResolution = resolution;
    this.pOversampling = oversampling;
    this.pRenderer = renderer;

    this.cRects = null;
    this.renderGraph();

    this.scaleContainer();
  }

  renderGraph() {
    if (this.cRects) {
      this.cRects.destroy();
    }
    const renderWidth = this.pResolution;
    const r = renderWidth / this.pDuration;

    // const rt = new PIXI.RenderTexture({
    //   width: renderWidth,
    //   height: this.pHeight,
    //   scaleMode: "linear",

    //   resolution: 1,
    // });

    // const sprite = new PIXI.Sprite(rt);
    // sprite.width = renderWidth;
    // sprite.height = this.pHeight;

    this.cRects = new PIXI.Graphics();
    this.cRects.roundRect(0, 0, this.pWidth, this.pHeight, 5);
    this.cRects.x = 0;
    this.cRects.y = 0;
    this.cRects.fill("white");

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
      const r_col = Math.round(rgb[0] * 255);
      const g_col = Math.round(rgb[1] * 255);
      const b_col = Math.round(rgb[2] * 255);
      const color = (r_col << 16) + (g_col << 8) + b_col;
      // const color = i % 2 === 0 ? 0xff0000 : 0x0000ff;

      const timesWidth =
        ((times[times.length - 1] + this.deltaTime) * this.pWidth) /
        (this.pEndTime - this.pStartTime);
      const x = (t - this.pStartTime) * (this.pWidth / (this.pEndTime - this.pStartTime));
      let width;
      if (i < times.length - 1) {
        const nextX =
          (times[i + 1] - this.pStartTime) * (this.pWidth / (this.pEndTime - this.pStartTime));
        width = nextX - x;
      } else {
        width = this.pWidth - x;
      }

      if (i === 0) {
        const rect = new PIXI.Graphics().roundRect(x, 0, width, this.pHeight, 5).fill(color);
        this.cRects.addChild(rect);
      } else if (i === times.length - 1) {
        const rect = new PIXI.Graphics().roundRect(x, 0, width, this.pHeight, 5).fill(color);
        this.cRects.addChild(rect);
      } else {
        const rect = new PIXI.Graphics().roundRect(x, 0, width, this.pHeight, 5).fill(color);
        this.cRects.addChild(rect);
      }
    });

    // this.pRenderer.render({
    //   container: colorRects,
    //   target: rt,
    // });
    // return colorRects;
    this.addChild(this.cRects);
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

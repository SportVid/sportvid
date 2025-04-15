import * as PIXI from "pixi.js";
import { DropShadowFilter } from "pixi-filters";

import * as Time from "../time.js";

export class TimeScale extends PIXI.Container {
  constructor(x, y, width, height, startTime = 0, endTime = 10) {
    super();
    this.pX = x;
    this.pY = y;
    this.pWidth = width;
    this.pHeight = height;
    this.pStartTime = startTime;
    this.pEndTime = endTime;

    this.pRangeSelection = null;
    this.pRangeSelectedColor = 0xd99090;

    this.pRect = null;
    this._drawBox();

    this.pBars_graphics = null;
    this._drawBars();
  }
  _drawBox() {
    if (this.pRect) {
      this.pRect.destroy();
    }
    this.pRect = new PIXI.Graphics();
    this.pRect.roundRect(0, 0, this.pWidth, this.pHeight, 5);
    this.pRect.x = this.pX;
    this.pRect.y = this.pY;
    this.pRect.fill(0xbbbbbb);

    // this.pMask = new PIXI.Graphics();
    // this.pMask.roundRect(0, 0, this.pWidth, this.pHeight, 5);
    // this.pMask.fill(0xffffff);
    // this.pRect.mask = this.pMask;

    // let shadow = new DropShadowFilter();
    // shadow.color = 0x0000;
    // shadow.distance = 2;
    // shadow.alpha = 0.4;
    // shadow.rotation = 90;
    // shadow.blur = 1;
    // this.pRect.filters = [shadow];

    this.addChild(this.pRect);
  }
  // _drawBars() {
  //   if (this.pBars_graphics) {
  //     this.pBars_graphics.destroy();
  //   }
  //   this.pBars_graphics = new PIXI.Container();
  //   this.pBars = [];

  //   const visibleDuration = Math.round(this.pEndTime - this.pStartTime);

  //   // determine optimal scaling
  //   const timeline_options = [30, 60, 150, 300, 600];
  //   var time_interval_length_in_s = visibleDuration / 10;
  //   var diff = 9999999;
  //   var best_option = 30;

  //   for (const option of timeline_options) {
  //     if (Math.abs(time_interval_length_in_s - option) < diff) {
  //       diff = Math.abs(time_interval_length_in_s - option);
  //       best_option = option;
  //     }
  //   }
  //   const time_interval_length_in_ms = best_option * 1000;

  //   const desired_num_of_minor_strokes = 4;

  //   const majorStroke = time_interval_length_in_ms;
  //   const minorStroke = time_interval_length_in_ms / desired_num_of_minor_strokes;

  //   const timestamps = Array(Math.ceil(this.pEndTime * 10))
  //     .fill(0)
  //     .map((_, i) => i);

  //   timestamps.forEach((time100) => {
  //     const timeFraction = Math.round(time100);
  //     const time = timeFraction / 10;
  //     const timeCode = Time.getTimecode(time, 0);
  //     let bar = {
  //       timeCode: timeCode,
  //       time: time,
  //       stroke: null,
  //       text: null,
  //     };
  //     if (this.pStartTime <= time && time <= this.pEndTime) {
  //       if ((time * 1000) % majorStroke == 0) {
  //         bar.stroke = this._drawStroke(time);
  //         bar.text = this._drawTime(time, timeCode);
  //         bar.stroke.height = this.pHeight - 25;

  //         bar.stroke.mask = this.pMask;
  //         bar.text.mask = this.pMask;

  //         this.pBars_graphics.addChild(bar.stroke);
  //         this.pBars_graphics.addChild(bar.text);
  //       } else if ((time * 1000) % minorStroke == 0) {
  //         bar.stroke = this._drawStroke(time);
  //         bar.stroke.height = this.pHeight - 35;

  //         bar.stroke.mask = this.pMask;

  //         this.pBars_graphics.addChild(bar.stroke);
  //       }
  //     }

  //     this.pBars.push(bar);
  //   });

  //   this.addChild(this.pBars_graphics);
  //   console.log("pBars_graphics children:", this.pBars_graphics.children);
  // }
  _drawBars() {
    if (this.pBars_graphics) {
      this.pBars_graphics.destroy();
    }
    this.pBars_graphics = new PIXI.Container();
    this.pBars = [];

    const interval = (this.pEndTime - this.pStartTime) / 5;
    const minorInterval = interval / 4;

    for (let time = this.pStartTime; time <= this.pEndTime; time += interval) {
      const x = this.timeToX(time);

      const mainStroke = new PIXI.Graphics();
      mainStroke.moveTo(x, 10);
      mainStroke.lineTo(x, 25);
      mainStroke.stroke({ color: 0x000000, pixelLine: true });
      this.pBars_graphics.addChild(mainStroke);

      const timeCode = Time.getTimecode(time, 2);
      const text = new PIXI.BitmapText({
        text: timeCode,
        style: { fontName: "Courier New", fontSize: 10 },
      });
      text.x = x;
      text.y = 26;
      text.tint = 0x000000;
      if (time === this.pStartTime) {
        text.anchor = { x: 0, y: 0 };
      } else if (time === this.pEndTime) {
        text.anchor = { x: 1, y: 0 };
      } else {
        text.anchor = { x: 0.5, y: 0 };
      }
      this.pBars_graphics.addChild(text);
    }

    for (let time = this.pStartTime; time <= this.pEndTime; time += minorInterval) {
      const x = this.timeToX(time);

      // Nebenstrich
      const minorStroke = new PIXI.Graphics();
      minorStroke.moveTo(x, 15);
      minorStroke.lineTo(x, 20);
      minorStroke.stroke({ color: 0x000000, pixelLine: true });
      this.pBars_graphics.addChild(minorStroke);
    }

    this.addChild(this.pBars_graphics);
  }
  _drawTime(time, timeCode) {
    const x = this.timeToX(time);
    const text = new PIXI.BitmapText({
      text: timeCode,
      style: { fontName: "default_font" },
    });
    text.x = x;
    text.y = 5;
    text.scale.set(0.5);
    text.tint = 0x000000;
    return text;
  }
  _drawStroke(time) {
    const x = this.timeToX(time);
    const path = new PIXI.Graphics().setStrokeStyle(1, 0x000000, 1).lineTo(0, 25).closePath();
    path.x = x;
    path.y = 25;
    return path;
  }
  timeToX(time) {
    return this.pX + this.timeScale * (time - this.pStartTime);
  }
  get timeScale() {
    return this.pWidth / (this.pEndTime - this.pStartTime);
  }
  _scale() {
    const visibleDuration = Math.round(this.pEndTime - this.pStartTime);

    // determine optimal scaling
    const timeline_options = [30, 60, 150, 300, 600];
    var time_interval_length_in_s = visibleDuration / 10;
    var diff = 9999999;
    var best_option = 30;

    for (const option of timeline_options) {
      if (Math.abs(time_interval_length_in_s - option) < diff) {
        diff = Math.abs(time_interval_length_in_s - option);
        best_option = option;
      }
    }
    const time_interval_length_in_ms = best_option * 1000;

    const desired_num_of_minor_strokes = 4;

    const majorStroke = time_interval_length_in_ms;
    const minorStroke = time_interval_length_in_ms / desired_num_of_minor_strokes;

    var largestX = 0;
    this.pBars.forEach((e) => {
      const time = e.time;

      if (this.pStartTime <= time && time <= this.pEndTime) {
        const x = this.timeToX(time);
        if ((time * 1000) % majorStroke == 0) {
          if (!e.text) {
            e.text = this._drawTime(time, e.timeCode);
            e.text.mask = this.pMask;

            this.pBars_graphics.addChild(e.text);
          }
          e.text.x = x;

          if (!e.stroke) {
            e.stroke = this._drawStroke(time);
            e.stroke.mask = this.pMask;
            this.pBars_graphics.addChild(e.stroke);
          }
          e.stroke.x = x;
          e.stroke.height = this.pHeight - 25;
        } else if ((time * 1000) % minorStroke == 0) {
          if (e.text) {
            e.text.destroy();
            e.text = null;
          }

          if (!e.stroke) {
            e.stroke = this._drawStroke(time);
            e.stroke.mask = this.pMask;
            this.pBars_graphics.addChild(e.stroke);
          }
          e.stroke.x = x;
          e.stroke.height = this.pHeight - 35;
        } else {
          if (e.stroke) {
            e.stroke.destroy();
            e.stroke = null;
          }
          if (e.text) {
            e.text.destroy();
            e.text = null;
          }
        }
        if (e.text && e.text.x <= largestX) {
          e.text.destroy();
          e.text = null;
        }

        if (e.text) {
          largestX = e.text.x + e.text.width;
        }
      } else {
        if (e.stroke) {
          e.stroke.destroy();
          e.stroke = null;
        }
        if (e.text) {
          e.text.destroy();
          e.text = null;
        }
      }
    });
  }

  selectRange(start, end) {
    if (this.pRangeSelection) {
      this.pRangeSelection.destroy();
      this.pRangeSelection = null;
    }

    const selectionRect = new PIXI.Graphics();

    const x = this.timeToX(start);

    const width = this.timeToX(end) - this.timeToX(start);
    const height = this.pHeight;

    selectionRect.roundRect(0, 0, width, height, 1);
    selectionRect.setStrokeStyle(2, this.pRangeSelectedColor, 1);
    selectionRect.x = x;
    selectionRect.fill(this.pRangeSelectedColor, 0.2);

    this.pRangeSelection = selectionRect;
    this.addChild(selectionRect);
  }
  removeSelectRange() {
    if (this.pRangeSelection) {
      this.pRangeSelection.destroy();
      this.pRangeSelection = null;
    }
  }
  set startTime(time) {
    this.pStartTime = time;
    this._scale();
  }
  get startTime() {
    return this.pStartTime;
  }
  set endTime(time) {
    this.pEndTime = time;
    this._scale();
  }
  get endTime() {
    return this.pEndTime;
  }
}

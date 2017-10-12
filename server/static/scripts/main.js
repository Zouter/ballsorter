var Directions, directions, fps, prepare, svgDirections, svgStage,
  bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; };

svgStage = 0;

svgDirections = 0;

directions = 0;

fps = 30;

requirejs(['jquery', 'd3', 'lodash', 'bootstrap'], function($, d3, _, bootstrap) {
  window.d3 = d3;
  return prepare();
});

prepare = function() {
  var addCounts, bininfo, color, data, evtSrc, gbincounts, height, img, initialize, line, margin, nframes, spanfps, width, x, xAxis, xaxis, y, yAxis;
  margin = {
    top: 20,
    right: 80,
    bottom: 30,
    left: 50
  };
  width = 960 - margin.left - margin.right;
  height = 300 - margin.top - margin.bottom;
  nframes = 500;
  x = d3.scaleLinear().range([0, width]).domain([0, nframes]);
  y = d3.scaleLinear().range([height, 0]).domain([0, 1]);
  color = d3.scaleOrdinal(d3.schemeCategory10);
  xAxis = d3.axisBottom().scale(x);
  yAxis = d3.axisLeft().scale(y);
  line = d3.line().x(function(d) {
    return x(d.frameid);
  }).y(function(d) {
    return y(d.count);
  });
  window.line = line;
  svgStage = d3.select("div#stage svg").attr("width", width + margin.left + margin.right).attr("height", height + margin.top + margin.bottom).append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");
  gbincounts = svgStage.append("g");
  xaxis = svgStage.append("g").attr("transform", "translate(0, " + height + ")").call(xAxis);
  img = d3.select("div#image").append("img");
  spanfps = d3.select("#fps");
  d3.select("#start").on("click", function() {
    console.log("start");
    return $.ajax({
      type: "GET",
      url: "/begin",
      dataType: "json"
    });
  });
  d3.select("#stop").on("click", function() {
    console.log("stop");
    return $.ajax({
      type: "GET",
      url: "/stop",
      dataType: "json"
    });
  });
  directions = new Directions(d3.select("div#directions svg"));
  evtSrc = new EventSource("/subscribe");
  evtSrc.onmessage = function(e) {
    var newData;
    newData = JSON.parse(e.data);
    console.log("Received " + newData.signal);
    if (newData.signal === "newCounts") {
      return addCounts(newData);
    } else if (newData.signal === "initialize") {
      return initialize(newData);
    } else if (newData.signal === "decision") {
      return directions.activateTube(newData.directionid);
    }
  };
  evtSrc.onopen = function(e) {
    return d3.select("#connected").html("<span class='glyphicon glyphicon-link'></span>&nbsp;Connected").attr("class", "btn btn-warning");
  };
  evtSrc.onerror = function(e) {
    console.log(e);
    if (e.readyState === EventSource.CLOSED) {
      return d3.select("#connected").html("<span class='glyphicon glyphicon-send'></span>&nbsp;Reconnect?").attr("class", "btn btn-default");
    }
  };
  bininfo = 0;
  data = 0;
  initialize = function(initialData) {
    var binlines, enter, lastframe;
    data = initialData;
    window.data = data;
    bininfo = data.bins;
    _.forEach(bininfo, function(bin) {
      return bin.counts = data.bincounts[bin.id];
    });
    binlines = gbincounts.selectAll("path").data(bininfo);
    lastframe = data.bincounts.length;
    x.domain([lastframe - nframes, lastframe]);
    xaxis.call(xAxis);
    enter = binlines.enter().append("path");
    enter.merge(binlines).attr("class", "line").attr("d", function(d) {
      return line(_.map(d.counts, function(count, i) {
        return {
          count: count,
          frameid: data.frameids[i]
        };
      }));
    }).style("stroke", function(d) {
      return d.color;
    });
    data.frametimes = [];
    return directions.initialize(initialData);
  };
  return addCounts = function(newdata) {
    var binlines, enter, fpsFrames, i, j, lastframe, newfps, ref, smooth;
    if (newdata.image) {
      img.attr("src", newdata.image);
    }
    bininfo.forEach(function(info) {
      return Array.prototype.push.apply(info.counts, newdata.newcounts[info.id]);
    });
    data.frameids.push(data.frameids[data.frameids.length - 1] + 1);
    binlines = gbincounts.selectAll("path").data(bininfo);
    lastframe = data.frameids[data.frameids.length - 1];
    x.domain([lastframe - nframes, lastframe]);
    enter = binlines.enter().append("path");
    enter.merge(binlines).attr("d", function(d) {
      return line(_.map(d.counts, function(count, i) {
        return {
          count: count,
          frameid: data.frameids[i]
        };
      }));
    });
    if (data.frameids.length > 2 * nframes) {
      bininfo.forEach(function(info) {
        return _.remove(info.counts, function(d, i) {
          return i < nframes;
        });
      });
      _.remove(data.frameids, function(d, i) {
        return i < nframes;
      });
    }
    xaxis.call(xAxis);
    for (i = j = 0, ref = newdata.newcounts[0].length - 1; 0 <= ref ? j <= ref : j >= ref; i = 0 <= ref ? ++j : --j) {
      data.frametimes.push(Date.now());
    }
    fpsFrames = 30;
    if (data.frametimes.length > fpsFrames) {
      newfps = fpsFrames / (Date.now() - data.frametimes[data.frametimes.length - fpsFrames - 1]) * 1000;
      smooth = 0.05;
      fps = fps + (newfps - fps) * smooth;
      return spanfps.text(Math.round(fps));
    }
  };
};

Directions = (function() {
  function Directions(container) {
    this.container = container;
    this.positionTube = bind(this.positionTube, this);
    this.width = 400;
    this.height = 600;
    this.container.attr("width", this.width).attr("height", this.height);
    this.margin = {
      top: 20,
      right: 20,
      bottom: 30,
      left: 20
    };
  }

  Directions.prototype.initialize = function(initialData) {
    var arc, garcs, pie;
    this.container.html("");
    this.cupradius = 30;
    this.ncups = initialData.directions.length;
    this.tubestart = {
      x: 0,
      y: 50
    };
    this.cupsradius = 200;
    this.tubebranch = {
      x: 0,
      y: this.height - this.margin.bottom - this.cupsradius
    };
    this.tubeend = {
      x: 0,
      y: this.height - this.cupradius
    };
    this.cupsarcangle = Math.PI / 2;
    this.cupsstartangle = Math.PI * 3 / 2 - this.cupsarcangle / 2;
    console.log(this.tubebranch);
    console.log(this.tubeend);
    this.gbottom = this.container.append("g").attr("transform", "translate(" + (this.width / 2) + ", " + this.tubeend.y + ")");
    arc = d3.arc().outerRadius(this.cupradius).innerRadius(0);
    pie = d3.pie().sort(null).value(1);
    this.gcups = this.gbottom.selectAll("g").data(initialData.directions).enter().append("g").attr("transform", (function(_this) {
      return function(d, i) {
        var cupCenter;
        cupCenter = _this.getCupCenter(i);
        return "translate(" + cupCenter.x + ", " + cupCenter.y + ")";
      };
    })(this));
    garcs = this.gcups.selectAll(".arc").data(function(d) {
      return pie(d);
    }).enter().append("g").attr("class", "arc");
    garcs.append("path").attr("d", arc).style("fill", function(d) {
      console.log(d.data);
      return d.data;
    }).style("stroke", "black").style("stroke-width", "5");
    this.gtubes = this.container.append("g").attr("transform", "translate(" + (this.width / 2) + ", " + this.margin.top + ")");
    this.ginactivetubes = this.gtubes.append("g");
    this.ginactivetubes.selectAll("path").data(initialData.directions).enter().append("path").attr("d", (function(_this) {
      return function(d, i) {
        return _this.positionTube(i);
      };
    })(this)).style("stroke", "#444444").style("fill", "none").style("stroke-width", "20").style("stroke-opacity", "0.5");
    this.activetube = this.gtubes.append("g").selectAll("path").data([0]).enter().append("path").style("stroke", "orange").style("fill", "none").style("stroke-width", "20");
    return this.activateTube(-1);
  };

  Directions.prototype.getCupCenter = function(i) {
    var angle;
    if (i === -1) {
      return {
        x: 0,
        y: 0
      };
    } else {
      angle = this.cupsstartangle + i / (this.ncups - 1) * this.cupsarcangle;
      console.log(angle);
      return {
        x: Math.cos(angle) * this.cupsradius,
        y: -Math.sin(angle) * this.cupsradius - this.cupsradius
      };
    }
  };

  Directions.prototype.positionTube = function(i) {
    var cupCenter;
    cupCenter = this.getCupCenter(i);
    return ("M" + this.tubestart.x + "," + this.tubestart.y + " L" + this.tubebranch.x + "," + this.tubebranch.y + " ") + ("L" + (cupCenter.x + this.tubeend.x) + "," + (cupCenter.y + this.tubeend.y - this.cupradius));
  };

  Directions.prototype.activateTube = function(i) {
    return this.activetube.data([i]).style("stroke", "red").transition().duration(1000).attr("d", (function(_this) {
      return function(d) {
        return _this.positionTube(d);
      };
    })(this)).style("stroke", "orange");
  };

  return Directions;

})();

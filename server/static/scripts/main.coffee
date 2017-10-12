svgStage = 0
svgDirections = 0

directions = 0

fps = 30

requirejs(['jquery', 'd3', 'lodash', 'bootstrap'],
($, d3, _, bootstrap) ->
    window.d3 = d3

    prepare()
)

prepare = () ->
    margin = {top: 20, right: 80, bottom: 30, left: 50}
    width = 960 - margin.left - margin.right
    height = 300 - margin.top - margin.bottom

    nframes = 500
    x = d3.scaleLinear()
        .range([0, width])
        .domain([0, nframes])

    y = d3.scaleLinear()
        .range([height, 0])
        .domain([0, 1])

    color = d3.scaleOrdinal(d3.schemeCategory10)

    xAxis = d3.axisBottom()
        .scale(x)

    yAxis = d3.axisLeft()
        .scale(y)

    line = d3.line()
        .x((d) -> x(d.frameid))
        .y((d) -> y(d.count))
    window.line = line
    svgStage = d3.select("div#stage svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

    gbincounts = svgStage.append("g")

    xaxis = svgStage.append("g")
        .attr("transform", "translate(0, " + (height) + ")")
        .call(xAxis)

    img = d3.select("div#image")
        .append("img")

    spanfps = d3.select("#fps")

    # Controls
    d3.select("#start").on("click", () ->
        console.log("start")
        $.ajax({type: "GET",url: "/begin",dataType: "json"})
    )
    d3.select("#stop").on("click", () ->
        console.log("stop")
        $.ajax({type: "GET",url: "/stop",dataType: "json"})
    )

    # directions
    directions = new Directions(d3.select("div#directions svg"))

    # initial initialization is finished, start listening for signals
    evtSrc = new EventSource("/subscribe");
    evtSrc.onmessage = (e) ->
        newData = JSON.parse(e.data)
        console.log("Received " + newData.signal)
        if newData.signal == "newCounts"
            addCounts(newData)
        else if newData.signal == "initialize"
            initialize(newData)
        else if newData.signal == "decision"
            directions.activateTube(newData.directionid)

    evtSrc.onopen = (e) ->
        d3.select("#connected")
            .html("<span class='glyphicon glyphicon-link'></span>&nbsp;Connected")
            .attr("class", "btn btn-warning")

    evtSrc.onerror = (e) ->
        console.log(e)
        if (e.readyState == EventSource.CLOSED)
            d3.select("#connected")
                .html("<span class='glyphicon glyphicon-send'></span>&nbsp;Reconnect?")
                .attr("class", "btn btn-default")

    bininfo = 0
    data = 0
    initialize = (initialData) ->
        data = initialData
        window.data = data

        bininfo = data.bins
        _.forEach(bininfo, (bin) -> bin.counts = data.bincounts[bin.id])

        # binlines
        binlines = gbincounts.selectAll("path")
            .data(bininfo)

        lastframe = data.bincounts.length

        x.domain([lastframe-nframes, lastframe])
        xaxis.call(xAxis)

        enter = binlines.enter()
            .append("path")

        enter.merge(binlines)
            .attr("class", "line")
            .attr("d", (d) -> line(_.map(d.counts, (count, i) -> {count:count, frameid:data.frameids[i]})))
            .style("stroke", (d) -> d.color)

        # fps
        data.frametimes = []

        # directions
        directions.initialize(initialData)

    addCounts = (newdata) ->
        if newdata.image
            img.attr("src", newdata.image)

        bininfo.forEach((info) -> Array.prototype.push.apply(info.counts, newdata.newcounts[info.id])) # appends the new data *in place*
        data.frameids.push(data.frameids[data.frameids.length-1]+1)

        binlines = gbincounts.selectAll("path")
            .data(bininfo)

        lastframe = data.frameids[data.frameids.length-1]

        x.domain([lastframe-nframes, lastframe])

        enter = binlines.enter()
            .append("path")

        enter.merge(binlines)
            #.transition()
            #.duration(10)
            #.ease(d3.easeLinear)
            .attr("d", (d) -> line(_.map(d.counts, (count, i) -> {count:count, frameid:data.frameids[i]})))

        # check if we should remove old data (and do it all at once)
        if data.frameids.length > 2*nframes
            bininfo.forEach((info) -> _.remove(info.counts, (d, i) -> i < nframes)) # appends the new data *in place*
            _.remove(data.frameids, (d, i) -> i < nframes)

        xaxis.call(xAxis)

        for i in [0..newdata.newcounts[0].length-1]
            data.frametimes.push(Date.now())

        fpsFrames = 30
        if data.frametimes.length > fpsFrames
            newfps =fpsFrames/(Date.now() - data.frametimes[data.frametimes.length - fpsFrames-1]) * 1000 # for milliseconds

            smooth = 0.05
            fps = fps + (newfps - fps) * smooth # smoothing the fps calculation

            spanfps.text(Math.round(fps))


class Directions
    constructor: (@container) ->
        @width = 400
        @height = 600
        @container.attr("width", @width)
                  .attr("height", @height)

        @margin = {top: 20, right: 20, bottom: 30, left: 20}

    initialize: (initialData) ->
        @container.html("")

        @cupradius = 30
        @ncups = initialData.directions.length
        @tubestart = {x:0, y:50}
        @cupsradius = 200 # radius of the circle on which the cups are positioned
        @tubebranch = {x:0, y:@height-@margin.bottom-@cupsradius}
        @tubeend = {x:0, y:@height-@cupradius}
        @cupsarcangle = Math.PI /2
        @cupsstartangle = Math.PI *3 / 2 - @cupsarcangle/2

        console.log(@tubebranch)
        console.log(@tubeend)

        # cups themselves
        @gbottom = @container.append("g")
            .attr("transform", "translate(#{@width/2}, #{@tubeend.y})")

        arc = d3.arc()
            .outerRadius(@cupradius)
            .innerRadius(0)

        pie = d3.pie()
            .sort(null)
            .value(1)

        @gcups = @gbottom.selectAll("g")
            .data(initialData.directions)
            .enter()
            .append("g")
            .attr("transform", (d, i) =>
                cupCenter = @getCupCenter(i)
                "translate(#{cupCenter.x}, #{cupCenter.y})")

        garcs = @gcups.selectAll(".arc")
            .data((d) -> pie(d))
            .enter()
            .append("g")
            .attr("class", "arc")

        garcs.append("path")
            .attr("d", arc)
            .style("fill", (d) -> console.log(d.data); return d.data)
            .style("stroke", "black")
            .style("stroke-width", "5")

        # tubes
        @gtubes = @container.append("g")
            .attr("transform", "translate(#{@width/2}, #{@margin.top})")

        # inactive tubes
        @ginactivetubes = @gtubes.append("g")
        @ginactivetubes.selectAll("path")
            .data(initialData.directions)
            .enter()
            .append("path")
            .attr("d", (d, i) => @positionTube(i))
            .style("stroke", "#444444")
            .style("fill", "none")
            .style("stroke-width", "20")
            .style("stroke-opacity", "0.5")
        # active tube
        @activetube = @gtubes.append("g")
            .selectAll("path")
            .data([0]) # datum doesn't seem to work here??
            .enter()
            .append("path")
            .style("stroke", "orange")
            .style("fill", "none")
            .style("stroke-width", "20")
        @activateTube(-1)

    getCupCenter: (i) ->
        if i == -1
            return {x:0, y:0}
        else
            #return {x:(i/(@ncups - 1) - 0.5) * (@width - @cupradius * 2 - @margin.left - @margin.right), y:0}
            angle = @cupsstartangle + i/(@ncups - 1) * @cupsarcangle
            console.log(angle)
            return {
                x: Math.cos(angle) * @cupsradius
                y: -Math.sin(angle) * @cupsradius - @cupsradius
            }

    positionTube: (i) =>
        cupCenter = @getCupCenter(i)
        "M#{@tubestart.x},#{@tubestart.y} L#{@tubebranch.x},#{@tubebranch.y} " +
        "L#{cupCenter.x+@tubeend.x},#{cupCenter.y+@tubeend.y-@cupradius}"

    activateTube: (i) ->
        @activetube
            .data([i])
            .style("stroke", "red")
            .transition()
            .duration(1000)
            .attr("d", (d) => @positionTube(d))
            .style("stroke", "orange")

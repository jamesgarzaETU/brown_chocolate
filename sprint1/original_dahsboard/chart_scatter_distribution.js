function chart_scatter_distribution(
  data,
  html_id,
  x={var:null, order:'as_appear'}, // Must be numeric
  y={var:null}, // Must be categorical
  id={var:null},

  title={value:null, size:40, weight:700, line:false},

  clr={var:null, value:'#e32726'}, // Variable containing color of bar(s)
  circle={radius:3, opacity:1.0}, // Variable containing radius and opacity of circles

  summary={
    var:'median', //'median' or 'mean'
    format:',.1f'
  },

  facet={var:null, size:18, weight:400, space_above_title:5, order:'as_appear'},
  group={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear'},
  switcher={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', line:false},
  scroll={var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:'as_appear', line:false},

  yaxis={
    height:400,
    range:[null, null],
    suffix:null,
    tick:{size:14, weight:400},
    label:{value:null, size:20, weight:700},
    offset: {top:10, bottom:10},
    show:true,
    show_line:true,
    show_ticks:true,
    num_ticks:null,
    show_grid:false
  },

  xaxis={
    tick:{size:16, weight:400},
    label:{value:null, size:20, weight:700},
    offset: {left:10, right:10},
    show:true,
    show_line:true,
    show_ticks:true,
    order:'as_appear' // 'as_appear' or 'alphabetical'
  },

  font={family:body_font},

  margin={top:10, bottom:10, left:10, right:10, g:10}
){


  // ----------------------------------------------->
  // ----- Function to calculate width of text ----->
  // ----------------------------------------------->

  function textWidth(text, fontSize=16, fontWeight=400, fontFamily=font.family) {

      // --- METHOD 1 --->
      /*container.append('text')
        .attr("x", -99999)
        .attr("y", -99999)
        .style("font-family", fontFamily)
        .style("font-size", fontSize + "px")
        .style("font-weight", fontWeight)
        .text(text);

      var text_width = container.node().getBBox().width;
      container.remove();

      console.log(text, '# WIDTH 1:', text_width, '# WIDTH 2:', context.measureText(text).width)

      return { text_width };*/



      // --- METHOD 2 --->
      var context = document.createElement('canvas').getContext('2d');
      context.font = fontWeight + ' ' + fontSize + 'px ' + fontFamily;

      return context.measureText(text).width;
  }

  // <-----------------------------------------------
  // <----- Function to calculate width of text -----
  // <-----------------------------------------------




  // ------------------------------------------------------------------->
  // ----- Function to return all indices of substring in a string ----->
  // ------------------------------------------------------------------->

  function getIndicesOf(searchStr, str, caseSensitive) {
      var searchStrLen = searchStr.length;
      if (searchStrLen == 0) {
          return [];
      }
      var startIndex = 0, index, indices = [];
      if (!caseSensitive) {
          str = str.toLowerCase();
          searchStr = searchStr.toLowerCase();
      }
      while ((index = str.indexOf(searchStr, startIndex)) > -1) {
          indices.push(index);
          startIndex = index + searchStrLen;
      }
      return indices;
  }

  // <-------------------------------------------------------------------
  // <----- Function to return all indices of substring in a string -----
  // <-------------------------------------------------------------------






  // ------------------------------------------------------------->
  // ----- Function to split text to fit into assigned width ----->
  // ------------------------------------------------------------->

  function splitWrapText(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family) {

      var textSplitWrapped = [];

      var textSplit = text.split(/\n|<br>/);

      textSplit.forEach(function(v){

          var spaces = getIndicesOf(' ', v);

          for(let numSplits = 0; numSplits <= spaces.length; numSplits++){
            // No split
            if(numSplits == 0){
              if(textWidth(v, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) <= width){
                textSplitWrapped.push(v);
                break;
               }
            }
            // At least one split
            else{
               var idealSplitPoints = [], actualSplitPoints = [], actualSplit = [];
               for(let split = 1; split <= numSplits; split++){
                 idealSplitPoints.push( parseInt((v.length/(numSplits+1))*split)-1 );
               }

               var usedSpaceIndex = 0;
               idealSplitPoints.forEach(function(vIdeal, iIdeal){
                 var idealVsSpace = [];
                 spaces.forEach(function(vSpace, iSpace){
                   if(vSpace > usedSpaceIndex){
                     idealVsSpace.push({
                       'ideal': vIdeal,
                       'space': vSpace,
                       'diffAbs': Math.abs(vSpace - vIdeal),
                       'diffAct': vSpace - vIdeal
                     });
                   }
                 })

                 if(idealVsSpace.length > 0){
                   var idealVsSpace = idealVsSpace.sort((a, b) => d3.ascending(a['diffAbs'], b['diffAbs']) || d3.ascending(a['diffAct'], b['diffAct']))

                   actualSplit.push( idealVsSpace[0]['space'] )
                   usedSpaceIndex = idealVsSpace[0]['space'];
                 }

               })
               actualSplit.push( v.length )


               var vSplit = [];
               var sliceStart = 0;
               actualSplit.forEach(function(vActualSplit){
                 vSplit.push(v.slice(sliceStart, vActualSplit))

                 sliceStart = vActualSplit+1;
               })

               var vSplitMaxWidth = 0;
               vSplit.forEach(function(v_vSplit){
                 if(textWidth(v_vSplit, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) > vSplitMaxWidth){ vSplitMaxWidth = textWidth(v_vSplit, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily); }
               })

               if(vSplitMaxWidth <= width){
                 vSplit.forEach(function(v_vSplit){
                   textSplitWrapped.push(v_vSplit)
                 })
                 break;
               }

               if(numSplits >= spaces.length ){
                 vSplit.forEach(function(v_vSplit){
                   textSplitWrapped.push(v_vSplit)
                 })
               }

             }

          }

          if(textSplitWrapped.length == 0){
            textSplitWrapped.push(v);
          }

      })

      return textSplitWrapped;
  }

  // <-------------------------------------------------------------
  // <----- Function to split text to fit into assigned width -----
  // <-------------------------------------------------------------





  // -------------------------------------------------------->
  // ----- Function to add TSPAN for each split-up text ----->
  // -------------------------------------------------------->

  function splitWrapTextSpan(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family, valign='bottom', dy_extra=0) {

    text.each(function() {

      var text = d3.select(this),
          lineNumber = 0,
          lineHeight = 1.1, // ems
          y = text.attr("y"),
          x = text.attr("x"),
          dy = parseFloat(text.attr("dy")),
          textSplit = splitWrapText(text.text(), width=width, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily),
          tspan = text.text(null);

      var vshift = (valign == 'bottom')? 0: (valign == 'top')? (1.1): (1.1/2)

      textSplit.forEach(function(v, i, a){

          text.append('tspan')
              .attr("x", x)
              .attr("y", y)
              .attr("dy", `${((i * lineHeight) - ((a.length-1)*vshift) + (dy_extra))}em`)
              .text(v)
      });
    })

  }

  // <--------------------------------------------------------
  // <----- Function to add TSPAN for each split-up text -----
  // <--------------------------------------------------------





  // ------------------------------------------------------------------------------>
  // ----- Function to split list of text elements to fit into assigned width ----->
  // ------------------------------------------------------------------------------>

  function splitWrapTextElement(list, width=100, padding=10, extra_width=0, fSize=14, fWeight=400, fFamily=font.family) {

      var listSplitWrapped = [];

      // Calculate total width of all elements in one row
      var totalWidthAllItems = 0;
      var spaces = [];
      var maxLinesInPrevRow = 0;
      var maxLinesInThisRow = 0;

      list.forEach(function(text, iList){

        if(iList > 0){
          spaces.push(totalWidthAllItems)
        }

        var textSplit = text.split(/\n|<br>/);

        var maxTextWidth = 0;
        maxLinesInThisRow = 0;
        var listSplitWrappedText = [];
        textSplit.forEach(function(vTextSplit, iTextSplit){

          var thisWidth = textWidth(vTextSplit, fSize, fWeight, fFamily) + (padding*2) + extra_width;
          maxTextWidth = (thisWidth > maxTextWidth)? thisWidth: maxTextWidth;

          maxLinesInThisRow = (iTextSplit > maxLinesInThisRow)? iTextSplit: maxLinesInThisRow;

          listSplitWrappedText.push({
            'value': vTextSplit,
            'dy': (iTextSplit*1.1) + 'em',
            'this-width-value': thisWidth,
            'max-width-value': maxTextWidth
          })
        })

        listSplitWrapped.push({
          'line': 0,
          'text': listSplitWrappedText,
          'x': totalWidthAllItems + padding,
          'y': 0*(maxLinesInPrevRow*(fSize*1.1)),
          //'y': ((maxLinesInPrevRow*(fSize*1.1)) + 10),
          'width-value': maxTextWidth
        })

        totalWidthAllItems += maxTextWidth;
      });
      maxLinesInPrevRow = maxLinesInThisRow;



      if(totalWidthAllItems < width){
        listSplitWrapped.forEach(function(v, i){
          v['x'] = v['x'] - (totalWidthAllItems/2)
        })
        return listSplitWrapped;
      }



      for(let numSplits = 1; numSplits <= (list.length-1); numSplits++){

          var listSplitWrapped = [];

          // ----- STEP 1: Split list into numSplits amount of smaller lists ----->

          var idealSplitPoints = [], actualSplitPoints = [], actualSplit = [];
          for(let split = 1; split <= numSplits; split++){
            idealSplitPoints.push( parseInt((totalWidthAllItems/(numSplits+1))*split) );
          }


          var usedSpaceIndex = 0;
          idealSplitPoints.forEach(function(vIdeal, iIdeal){
            var idealVsSpace = [];
            spaces.forEach(function(vSpace, iSpace){
              if(vSpace > usedSpaceIndex){
                idealVsSpace.push({
                  'index': iSpace+1,
                  'ideal': vIdeal,
                  'space': vSpace,
                  'diffAbs': Math.abs(vSpace - vIdeal),
                  'diffAct': vSpace - vIdeal
                });
              }
            })

            if(idealVsSpace.length > 0){
              var idealVsSpace = idealVsSpace.sort((a, b) => d3.ascending(a['diffAbs'], b['diffAbs']) || d3.ascending(a['diffAct'], b['diffAct']))

              actualSplit.push( idealVsSpace[0]['index'] )
              usedSpaceIndex = idealVsSpace[0]['index'];
            }

          })
          actualSplit.push( list.length )

          // Split list into numSplits amount of smaller lists
          var listSplit = [];
          var indexStart = 0;
          actualSplit.forEach(function(vActualSplit, iActualSplit){
            listSplit[iActualSplit] = list.slice(indexStart, vActualSplit)
            indexStart = vActualSplit;
          })

          // <----- STEP 1: Split list into numSplits amount of smaller lists -----



          var listSplitMaxWidth = 0;
          var maxLinesInPrevRow = 0;
          var prevY = 0;
          listSplit.forEach(function(v_listSplit, i_listSplit){

              var totalWidthThisLine = 0;
              var maxLinesInRow = 0;
              var maxLinesInThisRow = 0;

              v_listSplit.forEach(function(text, i){

                var textSplit = text.split(/\n|<br>/);

                maxLinesInThisRow = (textSplit.length > maxLinesInThisRow)? textSplit.length: maxLinesInThisRow;

                var maxTextWidth = 0;
                var listSplitWrappedText = [];
                textSplit.forEach(function(vTextSplit, iTextSplit, aTextSplit){

                  maxLinesInRow = (aTextSplit.length > maxLinesInRow)? aTextSplit.length: maxLinesInRow;

                  var thisWidth = (textWidth(vTextSplit, fSize, fWeight, fFamily) + (padding*2) + extra_width);

                  maxTextWidth = (thisWidth > maxTextWidth)? thisWidth: maxTextWidth;

                  listSplitWrappedText.push({
                    'value': vTextSplit,
                    'dy': (iTextSplit*1.1) + 'em',
                    'this-width-value': thisWidth,
                    //'max-width-value': maxTextWidth
                  })
                })

                listSplitWrappedText.forEach(function(v_listSplitWrappedText){
                  v_listSplitWrappedText['max-width-value'] = maxTextWidth
                })

                listSplitWrapped.push({
                  'line': i_listSplit,
                  'text': listSplitWrappedText,
                  'x': totalWidthThisLine + padding,
                  'width-value': maxTextWidth
                })

                totalWidthThisLine += maxTextWidth;

              });

              listSplitWrapped.forEach(function(v, i3){
                if(v['line'] == i_listSplit){
                  v['x'] = v['x'] - (totalWidthThisLine/2)
                  v['y'] = prevY + (maxLinesInPrevRow*(fSize*1.1)) + ((i_listSplit > 0)? (fSize*1.1): 0)
                }
              })

              maxLinesInPrevRow = maxLinesInThisRow;

              listSplitMaxWidth = (totalWidthThisLine > listSplitMaxWidth)? totalWidthThisLine: listSplitMaxWidth;
          })

          if(listSplitMaxWidth < width){ return listSplitWrapped; }
      }

      return listSplitWrapped;
  }

  // <------------------------------------------------------------------------------
  // <----- Function to split list of text elements to fit into assigned width -----
  // <------------------------------------------------------------------------------





  // ------------------------------------>
  // ----- Function to Scroll chart ----->
  // ------------------------------------>

  function scrollChart(method='up'){

    if(method == 'up'){
      var nextScrollIndex = ((scrollIndex+1) <= (domainScroll.length-1))? scrollIndex+1: 0;
    }
    else{
      var nextScrollIndex = ((scrollIndex-1) >= 0)? scrollIndex-1: (domainScroll.length-1);
    }



    // --- Move Scroll Texts --->
    svg.selectAll('.scroll_text_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${(canvas_width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(-canvas_width*1.5)}, ${height.scrollLabel})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('transform', function(){
              return `translate(${0}, ${height.scrollLabel})`
          })


    svg.selectAll('.scroll_text_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas_width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(canvas_width*1.5)}, ${height.scrollLabel})`
            }
          })




    // --- Move individual charts --->
    svg.select('.g_scroll_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('x', function(){
            (method == 'up')? canvas_width: -canvas_width
          })
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${((canvas_width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${((-canvas_width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('x', canvas_width*0)
          .attr('transform', function(){
              return `translate(${(margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
          })


    svg.select('.g_scroll_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('x', function(){
            (method == 'up')? -canvas_width: canvas_width
          })
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas_width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${(canvas_width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
          })


    if(method == 'up'){
      scrollIndex = ((scrollIndex+1) <= (domainScroll.length-1))? scrollIndex+1: 0;
    }
    else{
      scrollIndex = ((scrollIndex-1) >= 0)? scrollIndex-1: (domainScroll.length-1);
    }

  }

  // <------------------------------------
  // <----- Function to Scroll chart -----
  // <------------------------------------










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>

  // Get color of x
  var domainX = [];
  Array.from(new Set(data.map(d => d[x.var]))).forEach(function(v, i){
    domainX.push({
      'x': v,
      'color': (clr.var != null)? data.filter(d => d[x.var] == v).map(d => d[clr.var])[0]: ((clr.value != null)? clr.value: '#e32726')
      //'color': (clr.val != null)? clr.val: data.filter(d => d[x.var] == v).map(d => d[clr.var])[0]
    })
  })
  //var domainX = Array.from(new Set(data.map(d => d[x.var].toString())));
  //if(x.order == 'alphabetical'){ domainX.sort(); }
  console.log('domainX', domainX);



  // Facet domain
  var domainFacet = []
  if(facet.var != null){
    Array.from(new Set(data.map(d => d[facet.var].toString()))).forEach(function(vFacet, iFacet){
      var facetX = Array.from(new Set(data.filter(d => d[facet.var] == vFacet).map(d => d[x.var].toString())));
      if(x.order == 'alphabetical'){ facetX.sort(); }

      var facet_domainX = [];
      Array.from(new Set(data.filter(d => d[facet.var] == vFacet).map(d => d[x.var]))).forEach(function(vX, iX){
        facet_domainX.push({
          'x': vX,
          'color': (clr.var != null)? data.filter(d => d[facet.var] == vFacet && d[x.var] == vX).map(d => d[clr.var])[0]: ((clr.value != null)? clr.value: '#e32726')
        })
      })

      //domainFacet[iFacet] = {'facet': vFacet, 'x': facetX}
      domainFacet[iFacet] = {'facet': vFacet, 'x': facet_domainX}
    })
  }
  else{
    //domainFacet[0] = {'facet': null, 'x': domainX.map(d => d['x'])}
    domainFacet[0] = {'facet': null, 'x': domainX}
  }
  console.log('domainFacet', domainFacet);
  //console.log('###MEH:', domainFacet[0]['x']);



  // Get color of groups
  var domainGroup = [];
  if(group.var != null){
    Array.from(new Set(data.map(d => d[group.var]))).forEach(function(v, i){
      domainGroup.push({
        'group': v,
        'color': data.filter(d => d[group.var] == v).map(d => d[clr.var])[0]
      })
    })

  }
  else{
    domainGroup = [{'group':null, 'color':null}];
  }
  if(group.var != null && group.order == 'alphabetical'){ domainGroup.sort(); }
  //console.log('### domainGroup', domainGroup);


  // Switcher domain
  var domainSwitcher = (switcher.var != null)? Array.from(new Set(data.map(d => d[switcher.var]))): [null];
  if(switcher.var != null && switcher.order == 'alphabetical'){ domainSwitcher.sort(); }
  //console.log('### domainSwitcher', domainSwitcher);



  // Scroll domain
  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  //console.log('### domainScroll', domainScroll);



  // ID domain
  //var domainId = Array.from(new Set(data.map(d => d[id.var])));
  //console.log('### domainId', domainId);


  // <------------------------
  // <----- DATA DOMAINS -----
  // <------------------------










  // ------------------------>
  // ----- Graph Sizing ----->
  // ------------------------>

  var canvas_width = 960;


  var height = {};

  // Title Height
  height.title = 0;
  if(title.value != null){
    height.title = margin.g + (title.size*1.1)*splitWrapText(title.value, (canvas_width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family).length;
  }



  // Scroll Height
  height.scroll = 0;
  height.scrollLabel = 0;
  if(scroll.var != null ){

    domainScroll.forEach(function(vScroll, iScroll){
      var numScrollLines = splitWrapText(vScroll, (canvas_width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family).length;

      height.scroll = (((scroll.size*1.1)*numScrollLines) > height.scroll)? ((scroll.size*1.1)*numScrollLines): height.scroll;
    })

    if(scroll.label.value != null){
      var numScrollLabelLines = splitWrapText(scroll.label.value, (canvas_width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family).length;
      height.scrollLabel = numScrollLabelLines*(scroll.label.size*1.1) + 5
      height.scroll += height.scrollLabel
    }

    height.scroll += margin.g;
  }



  // Switcher Height
  height.switcher = 0;
  height.switcherLabel = 0;
  if(switcher.var != null ){
    var switcherText = splitWrapTextElement(domainSwitcher, width=canvas_width-(margin.left+margin.right), padding=16, extra_width=0, fSize=switcher.size, fWeight=switcher.weight, fFamily=font.family);

    var maxY = d3.max(switcherText.map(d => d['y']));
    var maxLine = d3.max(switcherText.map(d => d['line']));
    var maxRowInLastLine = 0;

    switcherText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
      if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
    });

    if(switcher.label.value != null){
      var numSwitchLabelLines = splitWrapText(switcher.label.value, (canvas_width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family).length;
      height.switcherLabel = numSwitchLabelLines*(switcher.label.size*1.1) + 5
      //height.switcher += height.switcherLabel
    }

    height.switcher = margin.g + maxY + (maxRowInLastLine*(switcher.size*1.1)) + 10 + height.switcherLabel
  }



  // Legend Height
  height.legend = 0;
  height.legendLabel = 0;
  if(group.var != null ){
    var legendText = splitWrapTextElement(domainGroup.map(d => d['group']), width=canvas_width-(margin.left+margin.right), padding=10, extra_width=14+5, fSize=group.size, fWeight=group.weight, fFamily=font.family);

    // Get colors
    legendText.forEach(function(v, i){
      v['color'] = domainGroup[i]['color']
    });

    if(group.label.value != null){
      var numLegendLabelLines = splitWrapText(group.label.value, (canvas_width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family).length;
      height.legendLabel = numLegendLabelLines*(group.label.size*1.1) + 5
      //height.legend += height.legendLabel
    }


    var maxY = d3.max(legendText.map(d => d['y']));
    var maxLine = d3.max(legendText.map(d => d['line']));
    var maxRowInLastLine = 0;

    legendText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
      if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
    });

    height.legend = maxY + (maxRowInLastLine*(group.size*1.1)) + height.legendLabel + 10
  }



  //height.yaxis = (yaxis.height*domainFacet.length) + (height.xaxis*domainFacet.length);
  //margin.yaxislabel = (yaxis.label.value != null)? (yaxis.label.size*1.1)*splitWrapText(yaxis.label.value, height.yaxis, fontSize=yaxis.label.size, fontWeight=yaxis.label.weight, fontFamily=font.family).length + (10) : 0;



  // --- Y-Axis --->

  // Scale
  var minYvalue = Infinity;
  var maxYvalue = -Infinity;
  data.forEach(function(v, i){
      minYvalue = (v[y.var] < minYvalue)? v[y.var]: minYvalue;
      maxYvalue = (v[y.var] > maxYvalue)? v[y.var]: maxYvalue;
  });

  var yScale = d3.scaleLinear()
    .domain([
      (yaxis.range[1] != null)? yaxis.range[1]: maxYvalue,
      (yaxis.range[0] != null)? yaxis.range[0]: minYvalue
    ])
    .range([
      yaxis.offset.top,
      yaxis.offset.top + yaxis.height
    ]);


  // Axis
  var yAxisChart = d3.axisLeft()
  .scale(yScale)
  .tickFormat((d) => (yaxis.suffix != null)? (d + yaxis.suffix): d);

  if(yaxis.num_ticks != null){
    yAxisChart.ticks(yaxis.num_ticks)
  }

  // <--- Y-Axis ---


  margin.yaxis = 0;
  yAxisChart.scale().ticks().forEach(function(v, i){
    if(textWidth(v + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight) > margin.yaxis){
      margin.yaxis = textWidth(v + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight)
    }
  })
  //console.log('margin.yaxis', margin.yaxis)




  // Y-Axis Label Margin
  margin.yaxislabel = (yaxis.label.value != null)? (yaxis.label.size*1.1)*splitWrapText(yaxis.label.value, yaxis.height, fontSize=yaxis.label.size, fontWeight=yaxis.label.weight, fontFamily=font.family).length + (10) : 0;

  // X-Axis Label Height
  height.xaxislabel = (xaxis.label.value != null)? (xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, canvas_width - (margin.left + margin.yaxislabel + margin.yaxis + margin.right), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length + (10) : 0;



  // --- X-Axis --->

  // Scale
  var facetLengths = [];
  domainFacet.forEach(function(vFacet, iFacet){
    facetLengths.push(vFacet['x'].length)
  })
  var maxFacetLength = facetLengths.reduce((a, b) => Math.max(a, b), -Infinity)

  var xWidth = (canvas_width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxislabel + margin.yaxis + xaxis.offset.left)
  var xScale = [], xAxisChart = [];
  domainFacet.forEach(function(v, i){

    xScale[i] = d3.scaleBand()
      .domain(v['x'].map(d => d['x']))
      .range([
        //margin.yaxislabel + margin.yaxis + xaxis.offset.left,
        //margin.yaxislabel + margin.yaxis + xaxis.offset.left + ((canvas_width - (margin.left + xaxis.offset.right + margin.right))*(v['x'].length/domainX.length))

        //margin.yaxislabel + margin.yaxis + xaxis.offset.left,
        //canvas_width - (margin.left + xaxis.offset.right + margin.right)

        //(margin.yaxislabel + margin.yaxis + xaxis.offset.left) + (xWidth*((1 - (v['x'].length/maxFacetLength))*0.5)),
        //margin.yaxislabel + margin.yaxis + xaxis.offset.left + (xWidth*(v['x'].length/maxFacetLength))

        (margin.yaxislabel + margin.yaxis + xaxis.offset.left) + (xWidth*((1 - (v['x'].length/maxFacetLength))*0.5)),
        margin.yaxislabel + margin.yaxis + xaxis.offset.left + xWidth - (xWidth*((1 - (v['x'].length/maxFacetLength))*0.5))

      ])
      .padding([0.01]);

    // Axis
    xAxisChart[i] = d3.axisBottom(xScale[i]);
  })

  // <--- X-Axis ---


  // X-axis Height (without x-axis label)
  var maxXtickLength = 1;
  domainX.forEach(function(vX, iX){
    maxXtickLength = Math.max(maxXtickLength, splitWrapText(vX['x'], xScale[0].bandwidth()*0.95, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).length)
  });
  //height.xaxis = ((xaxis.show)?(((xaxis.tick.size*1.1)*maxXtickLength) + 5): 0) + ( (xaxis.label.value != null)? (xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, (canvas_width - (margin.left + margin.yaxislabel + margin.yaxis + margin.right)), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length : 0 )
  height.xaxis = ((xaxis.show)?(((xaxis.tick.size*1.1)*maxXtickLength) + 5): 0)
  //console.log('maxXtickLength', maxXtickLength, 'height.xaxis:', height.xaxis)




  // Total Height of all Facet Labels and y-Positions of Facets
  var facet_ypos = [];
  height.facetLabel = [];
  height.facet = 0;

  var facetPos = 0;

  domainFacet.forEach(function(vFacet, iFacet){
    var numFacetLabelLines = (vFacet['facet'] != null)? splitWrapText(vFacet['facet'], (canvas_width - margin.left - margin.yaxislabel - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length: 0;
    height.facetLabel[iFacet] = (numFacetLabelLines*(facet.size*1.1)) + ((facet.var != null)? facet.space_above_title: 0);

    facet_ypos[iFacet] = facetPos + height.facetLabel[iFacet];

    facetPos += height.facetLabel[iFacet] + yaxis.offset.top + yaxis.height + yaxis.offset.bottom + height.xaxis;
  })

  height.facet += d3.sum(height.facetLabel);
  console.log('###facet_ypos:', facet_ypos)


  //height.xaxis = ((xaxis.show)?(xaxis.tick.size*1.1) + 15: 0) + ( (xaxis.label.value != null)? (xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, (canvas_width - (margin.left + margin.yaxislabel + margin.yaxis + margin.right)), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length : 0 )
  height.yaxis = (yaxis.height*domainFacet.length) + (height.xaxis*domainFacet.length);



  var canvas_height = margin.top + height.title + height.scroll + height.switcher + height.legend + height.facet + ((yaxis.offset.top+yaxis.height+yaxis.offset.bottom+height.xaxis)*domainFacet.length) + height.xaxislabel + margin.bottom;

  // <------------------------
  // <----- Graph Sizing -----
  // <------------------------










  // ---------------->
  // ----- AXES ----->
  // ---------------->

  // --- X-Axis --->
  /*
  // Scale
  var facetLengths = [];
  domainFacet.forEach(function(vFacet, iFacet){
    facetLengths.push(vFacet['x'].length)
  })
  var maxFacetLength = facetLengths.reduce((a, b) => Math.max(a, b), -Infinity)

  var xWidth = (canvas_width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxislabel + margin.yaxis + xaxis.offset.left)
  var xScale = [], xAxisChart = [];
  domainFacet.forEach(function(v, i){

    xScale[i] = d3.scaleBand()
      .domain(v['x'].map(d => d['x']))
      .range([
        //margin.yaxislabel + margin.yaxis + xaxis.offset.left,
        //margin.yaxislabel + margin.yaxis + xaxis.offset.left + ((canvas_width - (margin.left + xaxis.offset.right + margin.right))*(v['x'].length/domainX.length))

        //margin.yaxislabel + margin.yaxis + xaxis.offset.left,
        //canvas_width - (margin.left + xaxis.offset.right + margin.right)

        //(margin.yaxislabel + margin.yaxis + xaxis.offset.left) + (xWidth*((1 - (v['x'].length/maxFacetLength))*0.5)),
        //margin.yaxislabel + margin.yaxis + xaxis.offset.left + (xWidth*(v['x'].length/maxFacetLength))

        (margin.yaxislabel + margin.yaxis + xaxis.offset.left) + (xWidth*((1 - (v['x'].length/maxFacetLength))*0.5)),
        margin.yaxislabel + margin.yaxis + xaxis.offset.left + xWidth - (xWidth*((1 - (v['x'].length/maxFacetLength))*0.5))

      ])
      .padding([0.01]);

    // Axis
    xAxisChart[i] = d3.axisBottom(xScale[i]);
  })

  */
  // <--- X-Axis ---


  // --- Scale for shifting Circle Groups left/right on X-Axis bandwidth --->

  var circleShiftScale = d3.scaleLinear()
    .domain([
      0,
      domainGroup.length-1
    ])
    .range([
      -((domainGroup.length-1)*(((xScale[0].bandwidth()*0.9)/domainGroup.length)/2)),
      (domainGroup.length-1)*(((xScale[0].bandwidth()*0.9)/domainGroup.length)/2)
    ]);

  // <--- Scale for shifting Circle Groups left/right on X-Axis bandwidth ---


  // <----------------
  // <----- AXES -----
  // <----------------










  // ---------------->
  // ----- DATA ----->
  // ---------------->
  /*
  var yInfo = [];
  domainScroll.forEach(function(vScroll, iScroll){
    yInfo[iScroll] = []

    domainSwitcher.forEach(function(vSwitcher, iSwitcher){
      yInfo[iScroll][iSwitcher] = [];

      domainX.map(d => d['x']).forEach(function(vX, iX){
        yInfo[iScroll][iSwitcher][iX] = [];

        domainGroup.forEach(function(vGroup, iGroup){
            yInfo[iScroll][iSwitcher][iX][iGroup] = [];


            var dataSlice = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) && d[x.var] == vX);

            yInfo[iScroll][iSwitcher][iX][iGroup]['summary'] = {
              'median': d3.median(dataSlice, d => d[y.var]),
              'mean': d3.mean(dataSlice, d => d[y.var]),
            };

            yInfo[iScroll][iSwitcher][iX][iGroup]['y_bins'] = [];
            yInfo[iScroll][iSwitcher][iX][iGroup]['y_bins'].push({
              'text': vX,
              'bin': d3.bin().thresholds(d3.thresholdFreedmanDiaconis)(dataSlice.map(d => d[y.var]) ) //d3.thresholdFreedmanDiaconis thresholdScott thresholdSturges
            })

            yInfo[iScroll][iSwitcher][iX][iGroup]['y_bins'].forEach(function(vBin, iBin){

              vBin['bin'].forEach(function(vBinEntry, iBinEntry) {
                vBinEntry['size'] = vBinEntry.length;
              })

              vBin['scale'] = d3.scaleLinear()
                  .domain([
                    d3.min(vBin['bin'].map(d => d['size'])),
                    d3.max(vBin['bin'].map(d => d['size']))
                  ])
                  .range([0.01, 1]);
            })

        })
      })
    })
  })
  console.log('### yInfo', yInfo);

  var dataPlot = [];
  domainScroll.forEach(function(vScroll, iScroll){
    dataPlot[iScroll] = []

    domainSwitcher.forEach(function(vSwitcher, iSwitcher){
      dataPlot[iScroll][iSwitcher] = [];

      console.log('################')
      console.log('### SCROLL:', vScroll, '### SWITCHER:', vSwitcher)

      domainId.forEach(function(vId, iId){
        var dataObs = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && d[id.var] == vId)[0];
        //console.log('# dataObs:', dataObs)
        //console.log('#ID:', vId, '#indexes', iScroll, iSwitcher, domainX.map(d => d['x']).indexOf(dataObs[x.var]), (group.var != null)? domainGroup.map(d => d['group']).indexOf(dataObs[group.var]): 0)

        if(dataObs){
          console.log('#i:', iId, '#ID:', vId, '#indexes', iScroll, iSwitcher, domainX.map(d => d['x']).indexOf(dataObs[x.var]), (group.var != null)? domainGroup.map(d => d['group']).indexOf(dataObs[group.var]): 0)
          console.log('dataObs[x.var]', dataObs[x.var], 'dataObs[clr.var]', dataObs[clr.var], 'xScale(dataObs[x.var])', xScale(dataObs[x.var]))
            var binObs = yInfo[iScroll][iSwitcher][domainX.map(d => d['x']).indexOf(dataObs[x.var])][(group.var != null)? domainGroup.map(d => d['group']).indexOf(dataObs[group.var]): 0]['y_bins'][0];
            //console.log('# ID:', vId, '# BIN:', binObs)

            binObs['bin'].forEach(function(vBin, iBin){
              //console.log('vBin:', vBin)
              if (dataObs[y.var] >= vBin.x0 && dataObs[y.var] < vBin.x1){
                dataPlot[iScroll][iSwitcher].push({
                  'id': vId,
                  'x': dataObs[x.var],
                  //'x_jitter': xScale(dataObs[x.var]) + (xScale.bandwidth()*0.50 + circleShiftScale((group.var != null)? domainGroup.indexOf(dataObs[group.var]): 0)) + (((xScale.bandwidth()*0.45)/domainGroup.length) * (binObs['scale'](vBin['size'])) * ((2*Math.random()) -1)),
                  'x_jitter': xScale(dataObs[x.var]) ,
                  'y': dataObs[y.var],
                  'group': (group.var)? dataObs[group.var]: null,
                  'size': vBin['size'],
                  'color': dataObs[clr.var],
                  'opacity': 1,
                })
              }
            })
        }
        else{
          console.log('#i:', iId, '#ID:', vId, '#NO OBS:', iScroll, iSwitcher)
          dataPlot[iScroll][iSwitcher].push({
            'id': vId,
            'x': null,
            'x_jitter': null,
            'y': yScale.range()[1],
            'opacity': 0,
            'group': null,
            'size': null,
            'color': null,
            'opacity': 0,
          })
        }

      })
    })
  })
  console.log('dataPlot', dataPlot)
  */





  // Create data that has all combinations of all values
  var dataPlot = [];

  domainScroll.forEach(function(vScroll, iScroll){
    dataPlot[iScroll] = []

    domainSwitcher.forEach(function(vSwitcher, iSwitcher){
      dataPlot[iScroll][iSwitcher] = [];

      domainFacet.forEach(function(vFacet, iFacet){
        dataPlot[iScroll][iSwitcher][iFacet] = [];

        vFacet['x'].forEach(function(vX, iX){
          dataPlot[iScroll][iSwitcher][iFacet][iX] = [];

      /*domainX.map(d => d['x']).forEach(function(vX, iX){
        dataPlot[iScroll][iSwitcher][iX] = [];*/

          domainGroup.forEach(function(vGroup, iGroup){
              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup] = [];
              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['data'] = [];


              var dataSlice = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) && d[x.var] == vX['x']);

              //console.log('vScroll:', vScroll, 'vSwitcher:', vSwitcher, 'vFacet:', vFacet['facet'], 'vGroup:', vGroup['group'], 'vX:', vX)
              //console.log('dataSlice:', dataSlice)

              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['facet'] = (facet.var != null)? vX['x']: null,

              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['summary'] = {
                'median': d3.format(summary.format)(d3.median(dataSlice, d => d[y.var])),
                'mean': d3.format(summary.format)(d3.mean(dataSlice, d => d[y.var])),
              };

              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['y_bins'] = [];
              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['y_bins'].push({
                'text': vX['x'],
                'bin': d3.bin().thresholds(d3.thresholdFreedmanDiaconis)(dataSlice.map(d => d[y.var]) ) //d3.thresholdFreedmanDiaconis thresholdScott thresholdSturges
              })

              dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['y_bins'].forEach(function(vBin, iBin){

                vBin['bin'].forEach(function(vBinEntry, iBinEntry) {
                  vBinEntry['size'] = vBinEntry.length;
                })

                vBin['scale'] = d3.scaleLinear()
                    .domain([
                      d3.min(vBin['bin'].map(d => d['size'])),
                      d3.max(vBin['bin'].map(d => d['size']))
                    ])
                    .range([0.01, 1]);

                vBin['bin'].forEach(function(vBinEntry, iBinEntry) {
                  //console.log(childEntry.length)
                  vBinEntry.forEach(function(binArrayEntry, iBinArray) {

                    dataPlot[iScroll][iSwitcher][iFacet][iX][iGroup]['data'].push({
                      'y': binArrayEntry,
                      //'x_jitter': xScale(vX) + (xScale.bandwidth()*0.5) + (((xScale.bandwidth()*0.45)/domainGroup.length) * (vBin['scale'](vBinEntry['size'])) * ((2*Math.random()) -1)),
                      'x_jitter': xScale[iFacet](vX['x']) + (xScale[iFacet].bandwidth()*0.50 + circleShiftScale(iGroup)) + (((xScale[iFacet].bandwidth()*0.45)/domainGroup.length) * (vBin['scale'](vBinEntry['size'])) * ((2*Math.random()) -1)),
                      //'color': (clr.val != null)? clr.val: ((group.var != null)? domainGroup[iGroup]['color']: domainX[domainX.map(d => d['x']).indexOf(vX)]['color']),
                      //'color': (clr.var != null)? ((group.var != null)? domainGroup[iGroup]['color']: domainX[domainX.map(d => d['x']).indexOf(vX['x'])]['color']): ((clr.value != null)? clr.value: '#e32726'),
                      'color': (clr.var != null)? ((group.var != null)? domainGroup[iGroup]['color']: domainFacet[iFacet]['x'].filter(d => d['x'] == vX['x']).map(d => d['color'])[0]): ((clr.value != null)? clr.value: '#e32726'),
                      'group': (group.var != null)? vGroup['group']: null
                    })

                  })
                })
              })
          })
        })
      })
    })
  })
  console.log('### dataPlot', dataPlot);

  // <----------------
  // <----- DATA -----
  // <----------------










  // ----- Change height of parent DIV ----->
  /*d3.select(html_id)
    .style("height", (canvas_height + 10) + 'px') ;*/

  // ----- Create SVG element ----->
  var svg = d3.select(html_id)
      .append("div")
      .classed("svg-container", true)
      .append("svg")
      .attr("preserveAspectRatio", "xMinYMin meet")
      .attr("viewBox", "0 0 " + canvas_width + " " + canvas_height)
      .classed("svg-content", true)
      .append('g');

      /*d3.select(html_id)
      .append("svg")
      .attr("width", canvas_width)
      .attr("height", canvas_height)
      //.attr("viewBox", [-canvas_width/2, -canvas_height/2, canvas_width, canvas_height])
      //.attr("style", "max-width: 100%; height: auto; height: intrinsic;");*/





  // ----------------->
  // ----- TITLE ----->
  // ----------------->

  // Group
  var g_title = svg.append("g")
    .attr("class", "g_title")
    .attr('transform', `translate(${margin.left}, ${margin.top})`);


  //  Title Text
  if(title.value != null){
      g_title.selectAll('title_text')
          .data(splitWrapText(title.value, (canvas_width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family))
          .enter()
          .append("text")
            .style("font-family", font.family)
            .style("font-size", title.size +  "px")
            .style('font-weight', title.weight)
            .style("text-anchor", "middle")
            .style("dominant-baseline", "hanging")
            .attr("class", "title_text")
            .attr('x', margin.left + ((canvas_width - margin.left - margin.right)/2))
            .attr("dy", function(d, i){ return i*1.1 + 'em'})
            .text(d => d);

      if(title.line){
          g_title.append('path')
            .attr('d', 'M' + 0 + ',' + (height.title - (margin.g/2)) + 'L' + (canvas_width - (margin.left + margin.right)) + ',' + (height.title - (margin.g/2)))
            .attr('stroke', '#d3d2d2')
            .attr('stroke-width', '2')
      }
  }

  // <-----------------
  // <----- TITLE -----
  // <-----------------










  // ------------------>
  // ----- SCROLL ----->
  // ------------------>

  // Group
  var g_scroll = svg.append("g")
    .attr("class", "g_scroll")
    .attr('transform', `translate(${margin.left}, ${margin.top + height.title})`);


  if(scroll.var != null){

    // Scroll Label
    if(scroll.label.value != null){
        g_scroll.selectAll('scroll_title')
            .data(splitWrapText(scroll.label.value, (canvas_width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family))
            .enter()
            .append("text")
              .attr("class", "scroll_title")
              .style("font-family", font.family)
              .style("font-size", scroll.label.size +  "px")
              .style('font-weight', scroll.label.weight)
              .style("text-anchor", "middle")
              .style("dominant-baseline", "hanging")
              .attr('x', (canvas_width - margin.left - margin.right)/2)
              .attr("dy", function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



      var maxScrollWidth = 0;

      domainScroll.forEach(function(vScroll, iScroll){

          var scrollData = splitWrapText(vScroll, (canvas_width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family)

          g_scroll.selectAll('scroll_text')
              .data(scrollData)
              .enter()
              .append("text")
                .attr("class", "scroll_text_" + iScroll)
                .attr('opacity', function(){ return 1 - Math.min(iScroll, 1) })
                .style("font-family", font.family)
                .style("font-size", scroll.size +  "px")
                .style('font-weight', scroll.weight)
                .style("text-anchor", "middle")
                .style("dominant-baseline", "hanging")
                .attr('x', (canvas_width - margin.left - margin.right)/2)
                .attr('transform', `translate(${(Math.min(iScroll, 1)*canvas_width)}, ${height.scrollLabel})`)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .text(d => d);


          scrollData.forEach(function(vScroll2, iScroll2){
            maxScrollWidth = (textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family) > maxScrollWidth)? textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family): maxScrollWidth;
          })
      });


      var scrollIndex = 0;

      g_scroll.append('path')
            .attr("class", "scroll_right")
            .attr('d', 'M' + (canvas_width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas_width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas_width - (margin.left + margin.right))/2)-scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas_width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
            .attr("stroke", "#d3d2d2")
            .attr("fill", "#d3d2d2")
            .attr('transform', `translate(${-((maxScrollWidth/2) + 20)}, ${0})`)
            .on('click', function(event){
              scrollChart('down')
            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      g_scroll.append('path')
            .attr("class", "scroll_right")
            .attr('d', 'M' + (canvas_width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas_width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas_width - (margin.left + margin.right))/2)+scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas_width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
            .attr("stroke", "#d3d2d2")
            .attr("fill", "#d3d2d2")
            .attr('transform', `translate(${((maxScrollWidth/2) + 20)}, ${0})`)
            .on('click', function(event){
              scrollChart('up')
            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      if(scroll.line){
          g_scroll.append('path')
            .attr('d', 'M' + 0 + ',' + (height.scroll - (margin.g/2)) + 'L' + (canvas_width - (margin.left + margin.right)) + ',' + (height.scroll - (margin.g/2)))
            .attr('stroke', '#d3d2d2')
            .attr('stroke-width', '2')
      }

  }

  // <------------------
  // <----- SCROLL -----
  // <------------------










  // -------------------->
  // ----- SWITCHER ----->
  // -------------------->

  // Group
  var g_switcher = svg.append("g")
    .attr("class", "g_switcher")
    .attr('transform', `translate(${canvas_width/2}, ${margin.top + height.title + height.scroll})`);

  if(switcher.var != null){

    // Switcher Label
    if(switcher.label.value != null){
        g_switcher.selectAll('switch_title')
            .data(splitWrapText(switcher.label.value, (canvas_width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family))
            .enter()
            .append("text")
              .attr("class", "switcher_title")
              .style("font-family", font.family)
              .style("font-size", switcher.label.size +  "px")
              .style('font-weight', switcher.label.weight)
              .style("text-anchor", "middle")
              .style("dominant-baseline", "hanging")
              .attr('x', 0)
              .attr("dy", function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



    var switcherGroup = g_switcher.selectAll('.switcher')
        .data(switcherText)
        .enter()
        .append("g")
          .attr("class", function(d, i){ return "switcher switcher_" + i})
          .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.switcherLabel)})` })
          .attr("opacity", function(d, i){
            if(i == 0){ return 1.0 }
            else{ return 0.2 }
          })
          .on('click', (event, v) => {

                svg.selectAll('.switcher').attr('opacity', 0.2);
                svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);

                changeBars(event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1] )

          })
          .on("mouseover", function(d) {
              d3.select(this).style("cursor", "pointer");
          });


    switcherGroup.append("rect")
      .attr("class", function(d, i){ return "switcher_" + i})
      .attr('width-value', d => d['width-value'])
      //.attr('x', d => 0 - (d['width-value']/2))
      //.attr('x', -5)
      .attr('x', 5)
      .attr('y', -3)
      .attr('width', d => d['width-value']-8)
      .attr('height', d => (d['text'].length*(switcher.size*1.1)) + 6)
      .attr('fill', '#d3d2d2');


    switcherGroup.append("text")
      .attr("class", function(d, i){ return "switcher_" + i})
      .style("font-family", font.family)
      .style("font-size", switcher.size +  "px")
      .style('font-weight', switcher.weight)
      //.style("text-anchor", "start")
      .style("text-anchor", "middle")
      .style("dominant-baseline", "hanging")
      .attr('width-value', d => d['width-value'])
      .attr('x', 0)
      .each(function(d, i){
        d3.select(this).selectAll('.switcher_text_' + i)
          .data(d['text'])
          .enter()
          .append('tspan')
          //.attr('x', d => (d['max-width-value'] - d['this-width-value'])/2) // Centre-align horizontally
          .attr('x', d => d['max-width-value']/2) // Centre-align horizontally
          .attr('dy', d => d['dy'])
          .text( d => d['value'])
      });


    if(switcher.line){
        g_switcher.append('path')
          .attr('d', 'M' + 0 + ',' + (height.switcher - (margin.g/2)) + 'L' + (canvas_width - (margin.left+margin.right)) + ',' + (height.switcher - (margin.g/2)))
          .attr('stroke', '#d3d2d2')
          .attr('stroke-width', '2')
          .attr('transform', function(d){ return `translate(${(-(canvas_width/2)+margin.left)}, ${0})` })

    }
  }

  // <--------------------
  // <----- SWITCHER -----
  // <--------------------










  // ------------------>
  // ----- LEGEND ----->
  // ------------------>

  // Group
  var g_legend = svg.append("g")
    .attr("class", "g_legend")
    .attr('transform', `translate(${canvas_width/2}, ${margin.top + height.title + height.scroll + height.switcher})`);


  if(group.var != null){
      // Legend Label
      if(group.label.value != null){
          g_legend.selectAll('legend_title')
              .data(splitWrapText(group.label.value, (canvas_width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family))
              .enter()
              .append("text")
                .attr("class", "legend_title")
                .style("font-family", font.family)
                .style("font-size", group.label.size +  "px")
                .style('font-weight', group.label.weight)
                .style("text-anchor", "middle")
                .style("dominant-baseline", "hanging")
                .attr('x', 0)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
      }

      var legend = g_legend.selectAll('.legend')
          .data(legendText)
          .enter()
          .append("g")
            .attr("class", function(d, i){ return "legend_" + i})
            //.attr('transform', function(d){ return `translate(${d['x']}, ${d['y']})` })
            .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
            .attr("opacity", 1.0)
            .on('click', (event, v) => {

                  if(+event.currentTarget.getAttribute('opacity') == 1){
                      svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 0.2);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).style('opacity', 0);
                  }
                  else{
                      svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 1.0);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).style('opacity', 1);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).filter('.circ').transition().duration(200).style('opacity', (circle.opacity != null)? circle.opacity: 1.0);
                  }

            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      legend.append('rect')
        .attr("class", function(d, i){ return "legend_" + i})
        .attr('x', 0)
        .attr('width', group.size)
        .attr('height', group.size)
        .attr('fill', d => d['color']);

      legend.append("text")
        .attr("class", function(d, i){ return "legend_" + i})
        .style("font-family", font.family)
        .style("font-size", group.size +  "px")
        .style('font-weight', group.weight)
        .style("text-anchor", "start")
        .style("dominant-baseline", "hanging")
        .attr('width-value', d => d['width-value'])
        .attr('x', group.size + 5)
        .each(function(d, i){
          d3.select(this).selectAll('.legend_text_' + i)
            .data(d['text'])
            .enter()
            .append('tspan')
            .attr('x', group.size + 5)
            .attr('dy', d => d['dy'])
            .text( d => d['value'])
        });
  }

  // <------------------
  // <----- LEGEND -----
  // <------------------










  // ----------------->
  // ----- CHART ----->
  // ----------------->



  // ----- Group ----->
  var g_chart = svg.selectAll('.g_chart')
    .data(domainScroll)
    .enter()
    .append("g")
    .attr("class", function(d, i){ return "g_chart g_scroll_" + i})
    .attr('opacity', function(d, i){ return 1 - Math.min(i, 1) })
    .attr('x', function(d, i){
      return canvas_width*i
    })
    .attr('transform', function(d, i){
      return `translate(${((canvas_width*Math.min(1, i)) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
    });





  // ----- Add X-Axis Label to plot ----->
  if(xaxis.label.value != null){

      g_chart.append("text")
        .attr("class", "xaxis.label.value")
        .style("font-family", font.family)
        .style("font-size", xaxis.label.size + "px")
        .style('font-weight', xaxis.label.weight)
        .style("text-anchor", "middle")
        .style("dominant-baseline", "hanging")
        .attr('x', (margin.yaxislabel + margin.yaxis + xaxis.offset.left) + (((canvas_width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxislabel + margin.yaxis + xaxis.offset.left))*0.5) )
        .attr("y", canvas_height - margin.top - height.title - height.scroll - height.switcher - height.legend - height.xaxislabel - margin.bottom + 5)
        .text(xaxis.label.value)
        .call(splitWrapTextSpan, ((canvas_width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxislabel + margin.yaxis + xaxis.offset.left)), xaxis.label.size, xaxis.label.weight, font.family, valign='middle', dy_extra=0);

  }







    // ----- Add Circles to plot ----->
    dataPlot.forEach(function(vScroll, iScroll){

      //vScroll.forEach(function(vSwitcher, iSwitcher){
      vScroll[0].forEach(function(vFacet, iFacet){

        var g_facet = svg.select('.g_scroll_' + iScroll)
          .append('g')
          .attr("class", 'facet_' + iFacet)
          .attr('transform', `translate(${0}, ${facet_ypos[iFacet]})`)


        // ----- Facet Title ----->
        if(facet.var != null){
          g_facet.selectAll('facet_text')
              .data(splitWrapText(domainFacet[iFacet]['facet'], (canvas_width - margin.left - margin.yaxislabel - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
              .enter()
              .append("text")
                .style("font-family", font.family)
                .style("font-size", facet.size +  "px")
                .style('font-weight', facet.weight)
                .style("text-anchor", "middle")
                .style("dominant-baseline", "hanging")
                .attr("class", "facet_text")
                .attr('x', margin.yaxislabel + ((canvas_width - margin.left - margin.yaxislabel - margin.right)/2))
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .attr('transform', `translate(${0}, ${-height.facetLabel[iFacet] + facet.space_above_title})`)
                .text(d => d);

        }
        // <----- Facet Title -----





        // ----- Add Y-Axis Label to plot ----->
        if(yaxis.label.value != null){
            g_facet.append("text")
              .style("font-family", font.family)
              .style("font-size", yaxis.label.size + "px")
              .style('font-weight', yaxis.label.weight)
              .style("text-anchor", "middle")
              .style("dominant-baseline", "hanging")
              .attr('x', -(yScale.range()[0] + ((yScale.range()[1] - yScale.range()[0])*0.5)) ) // Moves vertically (due to rotation)
              .attr("y", 0) // Moves horizontally (due to rotation)
              .attr("transform", "rotate(-90)")
              .text(yaxis.label.value)
              .call(splitWrapTextSpan, height.yaxis, yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
        }
        // <----- Add Y-Axis Label to plot -----





        // ----- Add Y-Axis to plot ----->
        if(yaxis.show){

          if(yaxis.show_grid){

            //yAxisChart.tickSize(-((xScale[iFacet].range()[1] - xScale[iFacet].range()[0]) + xaxis.offset.left));

            var maxXrange = 0;
            xScale.forEach(function(v, i){
              maxXrange = Math.max(maxXrange, v.range()[1] - v.range()[0])
            })

            yAxisChart.tickSize(-(maxXrange + xaxis.offset.left));
          }

          var y_axis_chart = g_facet.append("g")
              .attr("class", "y_axis")
              .style("font-size", yaxis.tick.size + "px")
              .attr("transform", "translate(" + (margin.yaxislabel+margin.yaxis) + "," + 0 + ")")
              .call(yAxisChart);


          y_axis_chart.selectAll(".tick text")
              .attr("y", '0.0')
              .call(splitWrapTextSpan, ((canvas_width*0.4) - (margin.left + margin.yaxislabel)), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);

          // Remove Axis Line
          if(!yaxis.show_line){
            y_axis_chart.select(".domain").remove();
          }

          // Remove Axis Ticks
          if(!yaxis.show_ticks){
            y_axis_chart.selectAll(".tick").selectAll("line").remove();
          }

          if(yaxis.show_grid){
            y_axis_chart.selectAll(".tick line").attr("stroke", "#d3d2d2");
          }

        }
        // <----- Add Y-Axis to plot -----





        // ----- Add X-Axis to plot ----->

        if(xaxis.show){
          var x_axis_chart = g_facet.append("g")
              .attr("class", "x_axis_" + iFacet)
              .style("font-size", xaxis.tick.size + "px")
              .attr("transform", "translate(" + 0 + "," + (yaxis.offset.top + yaxis.height + yaxis.offset.bottom) + ")")
              .call(xAxisChart[iFacet]);

          x_axis_chart.selectAll(".tick text")
              .attr("x", '0.0')
              .call(splitWrapTextSpan, xScale[iFacet].bandwidth()*0.95, xaxis.tick.size, xaxis.tick.weight, font.family, valign='bottom', dy_extra=0.7);

          // Remove Axis Line
          if(!xaxis.show_line){
            x_axis_chart.select(".domain").remove();
          }

          // Remove Axis Ticks
          if(!xaxis.show_ticks){
            x_axis_chart.selectAll(".tick").selectAll("line").remove();
          }
        }
        // <----- Add X-Axis to plot -----




        vFacet.forEach(function(vX, iX){

          vX.forEach(function(vGroup, iGroup){

            //svg.select('.g_scroll_' + iScroll).selectAll('.data_circ_' + iScroll + '_' + iSwitcher + '_' + iX + '_' + iGroup)
            var g_data = g_facet.selectAll('.data_circ')
              .data(vGroup['data'])
              .enter()
              .append('g')
                .attr("class", function(d, i){
                  return 'scroll_' + iScroll +
                  ' switcher_0' +
                  ' facet_' + iFacet +
                  ' x_' + iX +
                  ' group_' + iGroup +
                  ' obs_' + iScroll + '_0_' + iFacet + '_' + iX + '_' + iGroup + '_' + i
                })
                .attr('color-value', d => d['color'])
                .attr('scroll-value', domainScroll[iScroll])
                .attr('switcher-value', domainSwitcher[0])
                .attr('group-value', domainGroup.map(d => d['group'])[iGroup])
                .attr('x-value', domainX.map(d => d['x'])[iX])
                .attr('jitter-value', d => d['x_jitter'])
                .attr('y-value', d => d['y'])
                .style("opacity", 1.0)
                .on('mouseover', (event, d) => {

                      // ----- Tooltip ----->

                      var thisX = +event.currentTarget.getAttribute("jitter-value") + margin.left;
                      var thisY = yScale(+event.currentTarget.getAttribute("y-value")) + (margin.top + height.title + height.scroll + height.switcher + height.legend);


                      var maxTextWidth = 0;
                      var rectHeight = 0;
                      var hoverText = [];
                      if(group.var != null){
                        hoverText.push({
                          'value':event.currentTarget.getAttribute("group-value"),
                          'size':group.size,
                          'weight':group.weight
                        })

                        rectHeight += (group.size*1.1);
                        maxTextWidth = (textWidth(event.currentTarget.getAttribute("group-value"), group.size, group.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute("group-value"), group.size, group.weight): maxTextWidth;
                      }

                      var scrollIndex = event.currentTarget.getAttribute("class").split(' ')[0].split('_')[1]
                      var switcherIndex = event.currentTarget.getAttribute("class").split(' ')[1].split('_')[1]
                      var facetIndex = event.currentTarget.getAttribute("class").split(' ')[2].split('_')[1]
                      var xIndex = event.currentTarget.getAttribute("class").split(' ')[3].split('_')[1]
                      var groupIndex = event.currentTarget.getAttribute("class").split(' ')[4].split('_')[1]
                      var obsIndex = event.currentTarget.getAttribute("class").split(' ')[5].split('_')[6]
                      //console.log('scrollIndex:', scrollIndex, 'switcherIndex:', switcherIndex, 'facetIndex:', facetIndex, 'xIndex:', xIndex, 'groupIndex:', groupIndex, 'obsIndex:', obsIndex)

                      var dataPoint = dataPlot[scrollIndex][switcherIndex][facetIndex][xIndex][groupIndex]['data'][obsIndex]
                      //console.log('dataPoint;', dataPoint)

                      thisY += facet_ypos[facetIndex]

                      hoverText.push({
                        'value': d3.format(',.1f')(dataPoint['y']) + ((yaxis.suffix != null)? yaxis.suffix: ''),
                        'size': yaxis.tick.size,
                        'weight': yaxis.tick.weight
                      });

                      rectHeight += (yaxis.tick.size*1.1);
                      maxTextWidth = (textWidth(d3.format(',.1f')(dataPoint['y']) + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight) > maxTextWidth)? textWidth(d3.format(',.1f')(dataPoint['y']) + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight): maxTextWidth;



                      if((thisX + (maxTextWidth*0.5) + 5) > (canvas_width - margin.right)){
                        var shift_left = Math.abs((canvas_width - margin.right) - (thisX + (maxTextWidth*0.5) + 5))
                      };


                      tooltip
                          .style('opacity', 1)
                          .attr('transform', `translate(${(thisX-(shift_left || 0))}, ${(thisY-rectHeight-6)})`)

                      tooltipRect.attr("stroke", function(){
                          if(event.currentTarget.getAttribute("color-value") == 'white' || event.currentTarget.getAttribute("color-value") == "rgb(255,255,255)" || event.currentTarget.getAttribute("color-value") == "#fff" || event.currentTarget.getAttribute("color-value") == "#ffffff"){
                            return '#d3d2d2'
                          }
                          else{
                            return event.currentTarget.getAttribute("color-value")
                          }
                        })
                        .attr("width", maxTextWidth + 20)
                        .attr("height", rectHeight+6)
                        .attr("x", -((maxTextWidth + 20)*0.5));

                      tooltipText.selectAll('tspan').remove();

                      var dy = 0;
                      hoverText.forEach(function(vHover, iHover){
                        tooltipText.append('tspan')
                            .style("font-size", vHover['size'])
                            .style("font-weight", vHover['weight'])
                            .attr("x", 0)
                            .attr("y", 0)
                            .attr("dy", dy + 'px')
                            .text(vHover['value']);

                        dy += 1.1*vHover['size'];
                      })

                      // <----- Tooltip -----


                })
                .on('mouseout', (event, v) => {
                        tooltip.style('opacity', 0).attr("transform", "translate(" + 0 + "," + 0 +")");
                });



          // ----- Add Circles ----->
          g_data.append('circle')
              .attr("class", function(d){
                return 'data_circ_' + iScroll + '_' + '0' + '_' + iX + '_' + iGroup +
                ' group_' + iGroup +
                ' circ'
              })
              .attr("fill", function(d){ return d['color'] })
              .attr("r", (circle.radius != null)?circle.radius :3)
              .attr("cx", d => d['x_jitter'])
              //.attr("cy", d => yScale.range()[1])
              .attr("cy", d => yScale(d['y']))
              .attr('scroll-value', domainScroll[iScroll])
              .attr('switcher-value', domainSwitcher[0])
              .attr('group-value', domainGroup.map(d => d['group'])[iGroup])
              .attr('x-value', domainX.map(d => d['x'])[iX])
              .attr('y-value', d => d['y'])
              .attr('color-value', d => d['color'])
              //.style("opacity", 0.0)
              .style("opacity", (circle.opacity != null)? circle.opacity: 1.0)
              //.transition()
              //  .duration(500)
              //  .attr("cy", d => yScale(d['y']))
              //  .style("opacity", (circle.opacity != null)? circle.opacity: 1.0)





          // ----- Add Summary Texts ----->


          // Create and place the "blocks" containing the circle and the text
          var g_summary = g_data.selectAll("summary_group")
              .data([vGroup['summary'][summary.var]])
              .enter()
              .append("g")
                .attr("class", "summary_group")
                .style('opacity', 0.0)
                .attr("transform", function(d){
                  //return "translate(" + ( xScale[iFacet](domainX.map(d => d['x'])[iX]) + ((xScale[iFacet].bandwidth()*0.5) - (((xScale[iFacet].bandwidth()*0.9)/domainGroup.length)/2)) + circleShiftScale(iGroup))   + "," + yScale.range()[1] + ")";
                  return "translate(" + ( xScale[iFacet](domainFacet[iFacet]['x'].map(d => d['x'])[iX]) + ((xScale[iFacet].bandwidth()*0.5) - (((xScale[iFacet].bandwidth()*0.9)/domainGroup.length)/2)) + circleShiftScale(iGroup))   + "," + yScale.range()[1] + ")";
                })
                .on("mouseover", function(event, d){
                    tooltip.style("opacity", 1);
                  })
                .on("mousemove", function(event, d){
                      tooltipText.selectAll('tspan').remove();

                      tooltipText.append('tspan')
                          .style("font-size", yaxis.tick.size + 'px')
                          .style("font-weight", yaxis.tick.weight)
                          .attr("x", 0)
                          .attr("y", 0)
                          //.attr("dy", 0)
                          .text(summary.var.charAt(0).toUpperCase() + summary.var.slice(1));

                      const x = event.layerX;
                      const y = event.layerY;
                      tooltip.attr('transform', `translate(${x+5}, ${y})`);
                    })
                .on("mouseout", function(event, d){
                      tooltip.style('opacity', 0);
                })



          // Add circle to block
          g_summary.append("circle")
                  .attr("class", "summary_circ")
                  .attr("r", "3")
                  .attr("stroke","black")
                  .attr("fill", "white");

          // Add dashed vertical line to slider
          g_summary.append("path")
              .attr("class", "summary_line")
              .attr("d", function(d){return 'M ' + 5 + ', ' + 0 + ' L ' + ((xScale[iFacet].bandwidth()*0.90)/domainGroup.length) + ', ' + 0 + ' Z'})
              .style("stroke-dasharray", ("5, 5"))
              .attr("stroke", "black")
              .attr("stroke-width", "1");

          // Add text to block
          g_summary.append("text")
            .attr("class", "summary_text")
              .style("font-family", font.family)
              .style("font-size", yaxis.tick.size + "px")
              .style('font-weight', yaxis.tick.weight)
              .style("text-anchor", "start")
              .style("dominant-baseline", "middle")
              .attr("transform", "translate(5, -10)")
              .style("opacity", 1.0)
              .text(function(d){return d + ((yaxis.suffix != null)?yaxis.suffix:'') });



          g_summary.transition()
          .duration(500)
          .delay(500)
            .style('opacity', 1.0)
            .attr("transform", function(d){
              //return "translate(" + (xScale[iFacet](domainX.map(d => d['x'])[iX]) - (xScale[iFacet].bandwidth()*0.01)) + "," + yScale(d) + ")";
              //return "translate(" + ( xScale[iFacet](domainX.map(d => d['x'])[iX]) + ((xScale[iFacet].bandwidth()*0.5) - (((xScale[iFacet].bandwidth()*0.9)/domainGroup.length)/2)) + circleShiftScale(iGroup))   + "," + yScale(d) + ")";
              return "translate(" + ( xScale[iFacet](domainFacet[iFacet]['x'].map(d => d['x'])[iX]) + ((xScale[iFacet].bandwidth()*0.5) - (((xScale[iFacet].bandwidth()*0.9)/domainGroup.length)/2)) + circleShiftScale(iGroup))   + "," + yScale(d) + ")";

            })



        });
      });
    });
  });


  // <-----------------
  // <----- CHART -----
  // <-----------------










  // ------------------->
  // ----- TOOLTIP ----->
  // ------------------->

  var tooltip = svg.append("g")
    .attr("class", "tooltip_" + html_id.slice(1))
    .style('opacity', 0);

  var tooltipRect =  tooltip.append('rect')
      .attr("class", "tooltip_" + html_id.slice(1) + "__rect")
      .attr('x', 0)
      .attr('y', -3)
      .attr('width', 0)
      .attr('height', 0)
      .attr("fill", "white")
      .attr("stroke", "black")
      .attr("stroke-width", "2");

  var tooltipText = tooltip.append('text')
    .style("text-anchor", "middle")
    .style("dominant-baseline", "hanging")
    .attr("class", "tooltip_" + html_id.slice(1) + "__text")
    .style("font-family", font.family)
    .attr('x', 0)
    .attr('y', 0)

  // <-------------------
  // <----- TOOLTIP -----
  // <-------------------





  // ---------------------->
  // ----- Zoom & Pan ----->
  // ---------------------->

  let zoom = d3.zoom()
    .on('zoom', handleZoom)
    .scaleExtent([0.5, 1])
    .translateExtent([[0, 0], [canvas_width, canvas_height]]);

  function handleZoom(e) {
    d3.select(html_id + ' svg g')
      .attr('transform', e.transform);
  }

  d3.select(html_id + ' svg')
    .call(zoom);

  // <----------------------
  // <----- Zoom & Pan -----
  // <----------------------


}

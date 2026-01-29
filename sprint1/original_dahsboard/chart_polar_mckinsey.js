function chart_polar(
  data,
  html_id,

  x={var:null, ci:{lower:null, upper:null}}, // Must be numeric
  y={var:null, order:'as_appear', ascending:true}, // Must be categorical

  title={value:[{size:40, weight:700, text:null}, {size:32, weight:700, text:null}], line:false},

  clr={
    var:'clr',
    palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
    value:'#e32726'
  }, // Variable containing color of bar(s), a name of a pre-defined palette of colors, or value to set all bars to same color
  line={width:1.5, opacity:1.0}, // Values of width and opacity of lines

  facet={var:null, size:18, weight:400, space_above_title:5, order:'as_appear', ascending:true},
  group={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true},
  switcher={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},
  scroll={var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},

  tooltip_text=[
    {size:14, weight:400, text:[{var:'pct', format:'.1f', prefix:null, suffix:'%'}]},
    {size:14, weight:400, text:[
      {var:'n', format:',.0f', prefix:null, suffix:null},
      {var:'tot', format:',.0f', prefix:'/', suffix:null}
    ]}
  ],

  xaxis={
    range:[null, null],
    suffix:null,
    format:null,
    offset:{left:10, right:10},
    tick:{size:10, weight:600, width:200, whiteSpace:'nowrap', overflow:'visible'},
    show:true,
    num_ticks:null,
    label:{value:null, size:10, weight:700, width:900, 
      whiteSpace:'nowrap', overflow:'visible'}
  },

  yaxis={
    height:600,
    offset:{top:90, bottom:90},
    tick:{size:10, weight:400, width:200, whiteSpace:'nowrap', overflow:'visible'},
    label:{value:null, size:10, weight:700, width:900, 
      whiteSpace:'nowrap', overflow:'visible'}
  },

  font={family:body_font},

  margin={top:50, bottom:50, left:100, right:10, g:10},

  canvas={width:1200},

  zoom=true

){


  // -------------------------->
  // ----- Color Palettes ----->
  // -------------------------->

  var palette = {
    'plotly': ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'],
    'd3': ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF'],
    'g10': ['#3366CC', '#DC3912', '#FF9900', '#109618', '#990099', '#0099C6', '#DD4477', '#66AA00', '#B82E2E', '#316395'],
    't10': ['#4C78A8', '#F58518', '#E45756', '#72B7B2', '#54A24B', '#EECA3B', '#B279A2', '#FF9DA6', '#9D755D', '#BAB0AC'],
    'alphabet': ['#AA0DFE', '#3283FE', '#85660D', '#782AB6', '#565656', '#1C8356', '#16FF32', '#F7E1A0', '#E2E2E2', '#1CBE4F', '#C4451C', '#DEA0FD', '#FE00FA', '#325A9B', '#FEAF16', '#F8A19F', '#90AD1C', '#F6222E', '#1CFFCE', '#2ED9FF', '#B10DA1', '#C075A6', '#FC1CBF', '#B00068', '#FBE426', '#FA0087'],
    //           Red         Orange     Yellow     Green     Blue       Indigo   Lavendar   Purple      Blue2      Pink     Yellowish     Brown2     Grey     
    'dark24': ['#FB0E0C', '#EC673C', '#FFFF00', '#1AA81D', '#2F91E5', '#6F00FE', '#750D86', '#511CFB', '#FB00D1', '#B2828D', '#A0C227', '#778AAE', '#862A16', '#A777F1', '#620042', '#1616A7', '#DA60CA', '#6C4516', '#0D2A63', '#AF0038'],    'light24': ['#FD3216', '#00FE35', '#6A76FC', '#FED4C4', '#FE00CE', '#0DF9FF', '#F6F926', '#FF9616', '#479B55', '#EEA6FB', '#DC587D', '#D626FF', '#6E899C', '#00B5F7', '#B68E00', '#C9FBE5', '#FF0092', '#22FFA7', '#E3EE9E', '#86CE00', '#BC7196', '#7E7DCD', '#FC6955', '#E48F72'],
    'set1': ['rgb(228,26,28)', 'rgb(55,126,184)', 'rgb(77,175,74)', 'rgb(152,78,163)', 'rgb(255,127,0)', 'rgb(255,255,51)', 'rgb(166,86,40)', 'rgb(247,129,191)', 'rgb(153,153,153)'],
    'pastel1': ['rgb(251,180,174)', 'rgb(179,205,227)', 'rgb(204,235,197)', 'rgb(222,203,228)', 'rgb(254,217,166)', 'rgb(255,255,204)', 'rgb(229,216,189)', 'rgb(253,218,236)', 'rgb(242,242,242)'],
  }

  var palette_names = [];
  for (const [key, value] of Object.entries(palette)) {
    palette_names.push(key);
  }

  // <--------------------------
  // <----- Color Palettes -----
  // <--------------------------





  // ----------------------------------------------->
  // ----- Function to calculate width of text ----->
  // ----------------------------------------------->

  function textWidth(text, fontSize=16, fontWeight=400, fontFamily=font.family) {

      // --- METHOD 1 --->
      /*container.append('text')
        .attr('x', -99999)
        .attr('y', -99999)
        .style('font-family', fontFamily)
        .style('font-size', fontSize + "px")
        .style('font-weight', fontWeight)
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

  /*function splitWrapText(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family) {

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
*/
function splitWrapText(text, width=200, fontSize=10, fontWeight=400, fontFamily=font.family) {
  // Get the angle of the text (you'll need to pass this as a parameter)
  var angle = arguments[5] || 0; // Default to 0 if not provided
  
  // Increase width for text at angels where space is more constrained
  var adjustedWidth = width;
  if (angle > 45 && angle < 135) {
      adjustedWidth = width * 0.7;
  } else if (angle > 225 && angle < 315) {
    adjustedWidth
  }
  // Don't wrap text at top (around 0/360°) or bottom (around 180°)
  if ((angle < 45 || angle > 315) || (angle > 135 && angle < 225)) {
      return [text];
  }
  
  // Wrap text on the sides
  var textSplitWrapped = [];
  var words = text.split(' ');
  var line = '';
  
  words.forEach(word => {
      var testLine = line + word + ' ';
      if (textWidth(testLine, fontSize, fontWeight, fontFamily) > width) {
          textSplitWrapped.push(line);
          line = word + ' ';
      } else {
          line = testLine;
      }
  });
  if (line) {
    textSplitWrapped.push(line.trim());
  }
  // Add extra spacing between lines based on angle
  if (textSplitWrapped.length > 1) {
    // Increase line spacing for text on sides
    if ((angle > 45 && angle < 135) || (angle > 225 && angle < 315)) {
        var spacedText = [];
        textSplitWrapped.forEach(line => {
            spacedText.push(line);
            spacedText.push(''); // Add empty line for extra spacing
        });
        textSplitWrapped = spacedText.slice(0, -1); // Remove last empty line
    }

    // Add extra spacing between lines for better readability
  if (textSplitWrapped.length > 1) {
    var spacedText = [];
    textSplitWrapped.forEach(line => {
      spacedText.push(line);
      spacedText.push(''); // Add empty line for extra spacing
    });
    textSplitWrapped = spacedText.slice(0, -1); // Remove last empty line
  }
}  
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
          y = text.attr('y'),
          x = text.attr('x'),
          dy = parseFloat(text.attr('dy')),
          textSplit = splitWrapText(text.text(), width=width, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily),
          tspan = text.text(null);

      var vshift = (valign == 'bottom')? 0: (valign == 'top')? (1.1): (1.1/2)

      textSplit.forEach(function(v, i, a){

          text.append('tspan')
              .attr('x', x)
              .attr('y', y)
              .attr('dy', `${((i * lineHeight) - ((a.length-1)*vshift) + (dy_extra))}em`)
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
            'dy': Math.min(1.1, (iTextSplit*1.1)) + 'em',
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

              prevY += (maxLinesInPrevRow*(fSize*1.1)) + ((i_listSplit > 0)? (fSize*1.1): 0)

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
              return `translate(${(canvas.width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(-canvas.width*1.5)}, ${height.scrollLabel})`
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
              return `translate(${(-canvas.width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(canvas.width*1.5)}, ${height.scrollLabel})`
            }
          })




    // --- Move individual charts --->
    svg.select('.scroll_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('x', function(){
            (method == 'up')? canvas.width: -canvas.width
          })
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${((canvas.width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${((-canvas.width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('x', canvas.width*0)
          .attr('transform', function(){
              return `translate(${(margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
          })


    svg.select('.scroll_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('x', function(){
            (method == 'up')? -canvas.width: canvas.width
          })
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas.width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${(canvas.width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
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





  // ----------------------------------->
  // ---- Function to change Lines ----->
  // ----------------------------------->

  function changeLines(iSwitch){

      dataPlot.forEach(function(vScroll, iScroll){
        vScroll.forEach(function(vFacet, iFacet){
            vFacet.forEach(function(vGroup, iGroup){

              // --- Change CI Area --->
              if(x.ci.lower != null && x.ci.upper != null){
                svg.select('.scroll_' + iScroll)
                  .select('.facet_' + iFacet)
                  .select('.group_' + iGroup)
                  .selectAll('.polar_ci_line')
                  .datum(vGroup[iSwitch]['data'])
                  .transition()
                    .duration(800)
                    .attr('switcher-value', iSwitch)
                    .attr("d", d3.area()
                      .x0(d => d['ci_l'])
                      .x1(d => d['ci_u'])
                      .y0(d => d['y_ci_l'])
                      .y1(d => d['y_ci_u'])
                      .curve(d3.curveLinearClosed)
                    );
              }

              // --- Change Lines --->
              svg.select('.scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .select('.group_' + iGroup)
                .selectAll('.polar_line')
                .datum(vGroup[iSwitch]['data'])
                .transition()
                  .duration(800)
                  .attr('switcher-value', iSwitch)
                  .attr('stroke', vGroup[iSwitch]['color'])
                  .attr('stroke-width', d => (line.width != null)? line.width: 1.5)
                  .attr("d", d3.line()
                    .x(d => d['x'])
                    .y(d => d['y'])
                    .curve(d3.curveLinearClosed)
                  );



              // --- Change circles --->
              svg.select('.scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .select('.group_' + iGroup)
                .selectAll('.polar_circ')
                .data(vGroup[iSwitch]['data'])
                .transition()
                  .duration(800)
                  .attr('switcher-value', iSwitch)
                  .attr('class', function(d, i){
                    return 'data_circ_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + iSwitch + '_' + i +
                    ' group_' + iGroup +
                    ' polar_circ'
                  })
                  .attr('cx', d => d['x'])
                  .attr('cy', d => d['y']);



          })
        })
      });

  };

  // <-----------------------------------
  // <---- Function to change Lines -----
  // <-----------------------------------





  // ---------------------------------------------->
  // ----- Function to create Ranges by Steps ----->
  // ---------------------------------------------->

  function range(start, stop, step) {
    if (typeof stop == 'undefined') {
        // one param defined
        stop = start;
        start = 0;
    }

    if (typeof step == 'undefined') {
        step = 1;
    }

    if ((step > 0 && start >= stop) || (step < 0 && start <= stop)) {
        return [];
    }

    var result = [];
    for (var i = start; step > 0 ? i < stop : i > stop; i += step) {
        result.push(i);
    }

    return result;
  };

  // <----------------------------------------------
  // <----- Function to create Ranges by Steps -----
  // <----------------------------------------------










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>

  // Scroll domain
  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  if(!scroll.ascending){domainScroll.reverse(); }
  //console.log('### domainScroll', domainScroll);



  // Y domain
  var domainY = [];
  Array.from(new Set(data.map(d => d[y.var]))).forEach(function(v, i){
    domainY.push({
      'y': v,
      //'color': (clr.var != null)? data.filter(d => d[y.var] == v).map(d => d[clr.var])[0]: ((clr.value != null)? clr.value: '#e32726')
    })
  })
  if(y.order == 'alphabetical'){ domainY.sort((a, b) => d3.ascending(a['y'], b['y'])); }
  if(!y.ascending){ domainY.reverse(); }

  //console.log('domainY', domainY);



  // Facet domain
  var domainFacet = []
  domainScroll.forEach(function(vScroll, iScroll){
    domainFacet[iScroll] = []

    if(facet.var != null){
      Array.from(new Set(data.map(d => d[facet.var].toString()))).forEach(function(vFacet, iFacet){
        var facetY = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[y.var].toString())));
        if(y.order == 'alphabetical'){ facetY.sort(); }
        if(!y.ascending){ facetY.reverse(); }

        var facet_domainY = [];
        Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[y.var]))).forEach(function(vY, iY){
          facet_domainY.push(vY)
        })

        domainFacet[iScroll][iFacet] = {'facet': vFacet, 'y': facet_domainY}
      })
    }
    else{
      domainFacet[iScroll][0] = {'facet': null, 'y': Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[y.var])))}
    }

    if(facet.order == 'alphabetical'){ domainFacet[iScroll].sort((a, b) => d3.ascending(a['facet'], b['facet'])); }
    if(!facet.ascending){ domainFacet[iScroll].reverse(); }
  })
  //console.log('domainFacet', domainFacet);



  // Group domain
  var domainGroup = [];
  if(group.var != null){
    Array.from(new Set(data.map(d => d[group.var]))).forEach(function(v, i){
      domainGroup.push({
        'group': v,
        'sortVar': (group.order != null && group.order != 'as_appear' && group.order != 'alphabetical')? data.filter(d => d[group.var] == v).map(d => d[group.order])[0]: null
      })
    })

  }
  else{
    domainGroup = [{
      'group':null,
      //'color':null
    }];
  }

  if(group.var != null && group.order == 'alphabetical'){
    domainGroup = domainGroup.sort((a, b) => d3.ascending(a['group'], b['group']));
  }
  if(group.var != null && group.order != null && group.order != 'as_appear' && group.order != 'alphabetical'){
    domainGroup = domainGroup.sort((a, b) => d3.ascending(a['sortVar'], b['sortVar']));
  }
  if(!group.ascending){ domainGroup.reverse(); }

  // Get colors for each group
  domainGroup.forEach(function(v, i){
    if(clr.var != null){
      v['color'] = data.filter(d => d[group.var] == v['group']).map(d => d[clr.var])[0];
    }
    else if(clr.palette != null && palette_names.includes(clr.palette.toLowerCase())){
      v['color'] = palette[clr.palette][i];
    }
    else if(clr.value != null){
      v['color'] = clr.value;
    }
    else{
      v['color'] = '#e32726';
    }
  })
  //console.log('### domainGroup', domainGroup);



  // Switcher domain
  var domainSwitcher = (switcher.var != null)? Array.from(new Set(data.map(d => d[switcher.var]))): [null];
  if(switcher.var != null && switcher.order == 'alphabetical'){ domainSwitcher.sort(); }
  if(!switcher.ascending){ domainSwitcher.reverse(); }
  //console.log('### domainSwitcher', domainSwitcher);


  // <------------------------
  // <----- DATA DOMAINS -----
  // <------------------------










  // ------------------------>
  // ----- Graph Sizing ----->
  // ------------------------>

  if (canvas == undefined){
    var canvas = {width:960}
  }
  if(canvas.width == null){
    canvas.width = 960;
  }


  var height = {};

  // Title Height
  /*height.title = 0;
  if(title.value != null){
    height.title = margin.g + (title.size*1.1)*splitWrapText(title.value, (canvas.width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family).length;
  }*/

  height.title = 0;
  var title_ypos = [];
  if(title.value != null){
    var totTitleHeight = 0
    title.value.forEach(function(vTitle, iTitle){
      title_ypos[iTitle] = height.title;

      height.title += (vTitle.size*1.1)*splitWrapText(vTitle.text, (canvas.width - margin.left - margin.right), fontSize=vTitle.size, fontWeight=vTitle.weight, fontFamily=font.family).length;
    })
    height.title += (margin.g);
  }



  // Scroll Height
  height.scroll = 0;
  height.scrollLabel = 0;
  if(scroll.var != null ){

    domainScroll.forEach(function(vScroll, iScroll){
      var numScrollLines = splitWrapText(vScroll, (canvas.width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family).length;

      height.scroll = (((scroll.size*1.1)*numScrollLines) > height.scroll)? ((scroll.size*1.1)*numScrollLines): height.scroll;
    })

    if(scroll.label.value != null){
      var numScrollLabelLines = splitWrapText(scroll.label.value, (canvas.width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family).length;
      height.scrollLabel = numScrollLabelLines*(scroll.label.size*1.1) + 5
      height.scroll += height.scrollLabel
    }

    height.scroll += margin.g;
  }



  // Switcher Height
  height.switcher = 0;
  height.switcherLabel = 0;
  if(switcher.var != null ){
    var switcherText = splitWrapTextElement(domainSwitcher, width=canvas.width-(margin.left+margin.right), padding=16, extra_width=0, fSize=switcher.size, fWeight=switcher.weight, fFamily=font.family);

    var maxY = d3.max(switcherText.map(d => d['y']));
    var maxLine = d3.max(switcherText.map(d => d['line']));
    var maxRowInLastLine = 0;

    switcherText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
      if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
    });

    if(switcher.label.value != null){
      var numSwitchLabelLines = splitWrapText(switcher.label.value, (canvas.width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family).length;
      height.switcherLabel = numSwitchLabelLines*(switcher.label.size*1.1) + 5
    }

    height.switcher = margin.g + maxY + (maxRowInLastLine*(switcher.size*1.1)) + 10 + height.switcherLabel
  }



  // Legend Height
  height.legend = 0;
  height.legendLabel = 0;
  if(group.var != null ){
    var legendText = splitWrapTextElement(domainGroup.map(d => d['group']), width=canvas.width-(margin.left+margin.right), padding=10, extra_width=14+5, fSize=group.size, fWeight=group.weight, fFamily=font.family);

    // Get colors
    legendText.forEach(function(v, i){
      v['color'] = domainGroup[i]['color']
    });

    if(group.label.value != null){
      var numLegendLabelLines = splitWrapText(group.label.value, (canvas.width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family).length;
      height.legendLabel = numLegendLabelLines*(group.label.size*1.1) + 5
    }


    var maxY = d3.max(legendText.map(d => d['y']));
    var maxLine = d3.max(legendText.map(d => d['line']));
    var maxRowInLastLine = 0;

    legendText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
      if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
    });

    height.legend = maxY + (maxRowInLastLine*(group.size*1.1)) + height.legendLabel + 10
  }




  // --- Calculate maximum text height taken up by radius labels (this helps define best outerRadius value) --->
  var maxY_LabelHeight = 0;
  domainY.forEach(function(vY, iY){

    var yHeight = (yaxis.tick.size*1.1)*splitWrapText(vY['y'], yaxis.tick.width, yaxis.tick.size, yaxis.tick.weight, font.family).length;

    if(yHeight > maxY_LabelHeight){
      maxY_LabelHeight = yHeight;
    }

  })
  //console.log('maxY_LabelHeight:', maxY_LabelHeight)


  var outerRadius = Math.min(
    (yaxis.height - (maxY_LabelHeight*2))/2,
    (canvas.width - (margin.left + margin.right) - (yaxis.tick.width*2))/2
  )
  //console.log('outerRadius:', outerRadius)




  // --- X-Axis --->

  // Scale
  var minXvalue = Infinity;
  var maxXvalue = -Infinity;
  data.forEach(function(v, i){
    minXvalue = (v[x.var] < minXvalue)? v[x.var]: minXvalue;
    maxXvalue = (v[x.var] > maxXvalue)? v[x.var]: maxXvalue;
  });


  var xScale = d3.scaleLinear()
    .domain([
      (xaxis.range[0] != null)? xaxis.range[0]: minXvalue,
      (xaxis.range[1] != null)? xaxis.range[1]: maxXvalue
    ])
    .range([0,(outerRadius*1.0)]);



  // Axis
  var xAxisChart = d3.axisBottom()
  .scale(xScale)
  .tickFormat((d) => (xaxis.suffix != null)? (d + xaxis.suffix): d);


  if(xaxis.num_ticks != null){
    xAxisChart.ticks(xaxis.num_ticks-1)
  }

  //xAxisChart.tickFormat((d) => (xaxis.suffix != null)? (d + xaxis.suffix): d);


  var xTicks = range(xScale.domain()[0], xScale.domain()[1], (xScale.domain()[1] - xScale.domain()[0])/(xaxis.num_ticks-1));



  var data_radius = [];
  domainFacet.forEach(function(vScroll, iScroll){
    data_radius[iScroll] = [];

    vScroll.forEach(function(vFacet, iFacet){
      data_radius[iScroll][iFacet] = [];

      vFacet['y'].forEach(function(v, i, a){

          data_radius[iScroll][iFacet].push({
            'segment': v,
            'startAngle': (i/a.length)*(2*Math.PI),
            'endAngle':((i+1)/a.length)*(2*Math.PI)
          })

      })
    });
  })
  //console.log('data_radius:', data_radius)

  // <--- X-Axis ---







  // Total Height of all Facet Labels and y-Positions of Facets
  var facet_ypos = [];
  height.facetLabel = [];
  height.facet = [];

  domainFacet.forEach(function(vScroll, iScroll){

    facet_ypos[iScroll] = [];
    height.facetLabel[iScroll] = [];
    height.facet[iScroll] = 0;

    var facetPos = 0;

    vScroll.forEach(function(vFacet, iFacet){
      var numFacetLabelLines = (vFacet['facet'] != null)? splitWrapText(vFacet['facet'], (canvas.width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length: 0;
      height.facetLabel[iScroll][iFacet] = (numFacetLabelLines*(facet.size*1.1)) + ((facet.var != null)? facet.space_above_title: 0);

      facet_ypos[iScroll][iFacet] = facetPos + height.facetLabel[iScroll][iFacet];

      facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + yaxis.height + yaxis.offset.bottom;
    })

    height.facet[iScroll] += d3.sum(height.facetLabel[iScroll]);
  })



  var maxFacets = 0
  domainFacet.forEach(function(vScroll, iScroll){
    maxFacets = Math.max(maxFacets, vScroll.length)
  })


  height.yaxis = (yaxis.height*maxFacets);



  var canvas_height = margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.facet) + ((yaxis.offset.top + yaxis.height + yaxis.offset.bottom)*maxFacets) + margin.bottom;

  /*console.log('margin.top', margin.top)
  console.log('height.title', height.title)
  console.log('height.scroll', height.scroll)
  console.log('height.switcher', height.switcher)
  console.log('height.legend', height.legend)
  console.log('height.facet', height.facet)
  console.log('d3.max(height.facet)', d3.max(height.facet))
  console.log('yaxis.offset.top', yaxis.offset.top)
  console.log('yaxis.height', yaxis.height)
  console.log('yaxis.offset.bottom', yaxis.offset.bottom)
  console.log('maxFacets', maxFacets)
  console.log('margin.bottom', margin.bottom)
  console.log('canvas_height', canvas_height)*/

  // <------------------------
  // <----- Graph Sizing -----
  // <------------------------










  // ---------------->
  // ----- DATA ----->
  // ---------------->


  // Create data that has all combinations of all values
  var dataPlot = [];

  domainScroll.forEach(function(vScroll, iScroll){
    dataPlot[iScroll] = []

    domainFacet[iScroll].forEach(function(vFacet, iFacet){
      dataPlot[iScroll][iFacet] = [];

      domainGroup.forEach(function(vGroup, iGroup){
        dataPlot[iScroll][iFacet][iGroup] = [];

        domainSwitcher.forEach(function(vSwitcher, iSwitcher){
          dataPlot[iScroll][iFacet][iGroup][iSwitcher] = [];

          var dataSlice = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) );

          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'] = [];
          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['group'] = (group.var != null)? vGroup['group']: null;
          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['color'] = (clr.var != null || clr.palette != null)? ((group.var != null)? domainGroup[iGroup]['color']: ((clr.value != null)? clr.value: '#e32726')): ((clr.value != null)? clr.value: '#e32726');


          if(dataSlice.length > 0){

            vFacet['y'].forEach(function(vY, iY){
              var dataObs = dataSlice.filter(d => d[y.var] == vY)[0]


              var angle = (dataObs != null)? 360*(vFacet['y'].indexOf(dataObs[y.var]) / vFacet['y'].length): null;
              var radius = (dataObs != null)? xScale(dataObs[x.var]): null;
              var radius_ci_l = (x.ci.lower != null)? (((dataObs != null)? xScale(dataObs[x.ci.lower]): null)): ((dataObs != null)? xScale(dataObs[x.var]): null);
              var radius_ci_u = (x.ci.upper != null)? (((dataObs != null)? xScale(dataObs[x.ci.upper]): null)): ((dataObs != null)? xScale(dataObs[x.var]): null);

              var newObs = {
                'x': (radius != null)? radius * Math.sin(Math.PI * 2 * angle / 360): null,
                'y': (radius != null)? -(radius * Math.cos(Math.PI * 2 * angle / 360)): null,
                'x_orig': (dataObs != null)? dataObs[x.var]: null,
                'y_orig': (dataObs != null)? dataObs[y.var]: null,

                // Confidence Interval Lines
                'ci_l': (radius_ci_l != null)? radius_ci_l * Math.sin(Math.PI * 2 * angle / 360): null,
                'y_ci_l': (radius_ci_l != null)? -(radius_ci_l * Math.cos(Math.PI * 2 * angle / 360)): null,
                'ci_u': (radius_ci_u != null)? radius_ci_u * Math.sin(Math.PI * 2 * angle / 360): null,
                'y_ci_u': (radius_ci_u != null)? -(radius_ci_u * Math.cos(Math.PI * 2 * angle / 360)): null,

                'ci_l_orig': (x.ci.lower != null && dataObs != null)? dataObs[x.ci.lower]: (dataObs != null)? dataObs[x.var]:null,
                'ci_u_orig': (x.ci.upper != null && dataObs != null)? dataObs[x.ci.upper]: (dataObs != null)? dataObs[x.var]:null,

                'group': (group.var != null)? vGroup['group']: null
              }


              if(tooltip_text != null){
                tooltip_text.forEach((v, i) => {
                    v['text'].forEach((v2, i2) => {
                      newObs[v2['var']] = (dataObs)?dataObs[v2['var']]: null
                    })
                });
              }

              dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].push(newObs);

            })


            // --- Forward fill observations --->
            var prevX = null;
            var prevY = null;
            var prevX_orig = null;
            var prevY_orig = null;

            var prev_ci_l = null;
            var prev_y_ci_l = null;
            var prev_ci_u = null;
            var prev_y_ci_u = null;
            var prev_ci_l_orig = null;
            var prev_ci_u_orig = null;

            if(tooltip_text != null){
              var prev_tooltip = {};
              tooltip_text.forEach((v1, i1) => {
                  v1['text'].forEach((v2, i2) => {
                    prev_tooltip[v2['var']] = null;
                  })
              });
            }

            dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].forEach(function(v, i){
              if (i == 0){
                prevX = null;
                prevY = null;
                prevX_orig = null;
                prevY_orig = null;

                prev_ci_l = null;
                prev_y_ci_l = null;
                prev_ci_u = null;
                prev_y_ci_u = null;
                prev_ci_l_orig = null;
                prev_ci_u_orig = null;

                if(tooltip_text != null){
                  tooltip_text.forEach((v1, i1) => {
                      v1['text'].forEach((v2, i2) => {
                        prev_tooltip[v2['var']] = null;
                      })
                  });
                }
              }


              if (i > 0){
                v['x'] = (v['x'] == null)? prevX: v['x'];
                v['y'] = (v['y'] == null)? prevY: v['y'];
                v['x_orig'] = (v['x_orig'] == null)? prevX_orig: v['x_orig'];
                v['y_orig'] = (v['y_orig'] == null)? prevY_orig: v['y_orig'];

                v['ci_l'] = (v['ci_l'] == null)? prev_ci_l: v['ci_l'];
                v['y_ci_l'] = (v['y_ci_l'] == null)? prev_y_ci_l: v['y_ci_l'];
                v['ci_u'] = (v['ci_u'] == null)? prev_ci_u: v['ci_u'];
                v['y_ci_u'] = (v['y_ci_u'] == null)? prev_y_ci_u: v['y_ci_u'];
                v['ci_l_orig'] = (v['ci_l_orig'] == null)? prev_ci_l_orig: v['ci_l_orig'];
                v['ci_u_orig'] = (v['ci_u_orig'] == null)? prev_ci_u_orig: v['ci_u_orig'];

                if(tooltip_text != null){
                  tooltip_text.forEach((v1, i1) => {
                      v1['text'].forEach((v2, i2) => {
                        v[v2['var']] = (v[v2['var']] == null)? prev_tooltip[v2['var']]: v[v2['var']]
                      })
                  });
                }
              }

              prevX = v['x'];
              prevY = v['y'];
              prevX_orig = v['x_orig'];
              prevY_orig = v['y_orig'];

              prev_ci_l = v['ci_l'];
              prev_y_ci_l = v['y_ci_l'];
              prev_ci_u = v['ci_u'];
              prev_y_ci_u = v['y_ci_u'];
              prev_ci_l_orig = v['ci_l_orig'];
              prev_ci_u_orig = v['ci_u_orig'];

              if(tooltip_text != null){
                tooltip_text.forEach((v1, i1) => {
                    v1['text'].forEach((v2, i2) => {
                      prev_tooltip[v2['var']] = v[v2['var']];
                    })
                });
              }
            })
            // <--- Forward fill observations ---



            // --- Reverse fill observations --->
            var prevX = null;
            var prevY = null;
            var prevX_orig = null;
            var prevY_orig = null;

            var prev_ci_l = null;
            var prev_y_ci_l = null;
            var prev_ci_u = null;
            var prev_y_ci_u = null;
            var prev_ci_l_orig = null;
            var prev_ci_u_orig = null;

            if(tooltip_text != null){
              var prev_tooltip = {};
              tooltip_text.forEach((v1, i1) => {
                  v1['text'].forEach((v2, i2) => {
                    prev_tooltip[v2['var']] = null
                  })
              });
            }

            dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].reverse().forEach(function(v, i){
              if (i == 0){
                prevX = null;
                prevY = null;
                prevX_orig = null;
                prevY_orig = null;

                prev_ci_l = null;
                prev_y_ci_l = null;
                prev_ci_u = null;
                prev_y_ci_u = null;
                prev_ci_l_orig = null;
                prev_ci_u_orig = null;

                if(tooltip_text != null){
                  tooltip_text.forEach((v1, i1) => {
                      v1['text'].forEach((v2, i2) => {
                        prev_tooltip[v2['var']] = null
                      })
                  });
                }
              }


              if (i > 0){
                v['x'] = (v['x'] == null)? prevX: v['x'];
                v['y'] = (v['y'] == null)? prevY: v['y'];
                v['x_orig'] = (v['x_orig'] == null)? prevX_orig: v['x_orig'];
                v['y_orig'] = (v['y_orig'] == null)? prevY_orig: v['y_orig'];

                v['ci_l'] = (v['ci_l'] == null)? prev_ci_l: v['ci_l'];
                v['y_ci_l'] = (v['y_ci_l'] == null)? prev_y_ci_l: v['y_ci_l'];
                v['ci_u'] = (v['ci_u'] == null)? prev_ci_u: v['ci_u'];
                v['y_ci_u'] = (v['y_ci_u'] == null)? prev_y_ci_u: v['y_ci_u'];
                v['ci_l_orig'] = (v['ci_l_orig'] == null)? prev_ci_l_orig: v['ci_l_orig'];
                v['ci_u_orig'] = (v['ci_u_orig'] == null)? prev_ci_u_orig: v['ci_u_orig'];

                if(tooltip_text != null){
                  tooltip_text.forEach((v1, i1) => {
                      v1['text'].forEach((v2, i2) => {
                        v[v2['var']] = (v[v2['var']] == null)? prev_tooltip[v2['var']]: v[v2['var']]
                      })
                  });
                }
              }

              prevX = v['x'];
              prevY = v['y'];
              prevX_orig = v['x_orig'];
              prevY_orig = v['y_orig'];

              prev_ci_l = v['ci_l'];
              prev_y_ci_l = v['y_ci_l'];
              prev_ci_u = v['ci_u'];
              rev_y_ci_u = v['y_ci_u'];
              prev_ci_l_orig = v['ci_l_orig'];
              prev_ci_u_orig = v['ci_u_orig'];

              if(tooltip_text != null){
                tooltip_text.forEach((v1, i1) => {
                    v1['text'].forEach((v2, i2) => {
                      prev_tooltip[v2['var']] = v[v2['var']];
                    })
                });
              }
            })


            dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].reverse()
            // <--- Reverse fill observations ---



            /*dataSlice.forEach(function(vObs, iObs){
              var angle = 360*(vFacet['y'].map(d => d['y']).indexOf(vObs[y.var]) / vFacet['y'].length);
              var radius = xScale(vObs[x.var]);

              dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].push({
                'x': radius * Math.sin(Math.PI * 2 * angle / 360),
                'y': -(radius * Math.cos(Math.PI * 2 * angle / 360)),
                'x_orig': vObs[x.var],
                'y_orig': vObs[y.var],
                'group': (group.var != null)? vObs['group']: null
              })

              if(y.order == 'alphabetical'){ if(y.order == 'alphabetical'){ dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].sort((a, b) => d3.ascending(a['y_orig'], b['y_orig'])); } }
            })*/
          }

        })
      })
    })
  })
  //console.log('### dataPlot', dataPlot);

  // <----------------
  // <----- DATA -----
  // <----------------










  // ----- Change height of parent DIV ----->
  /*d3.select(html_id)
    .style('height', (canvas_height + 10) + 'px') ;*/

  // ----- Create SVG element ----->
  var svg = d3.select(html_id)
      .append("div")
      .classed("svg-container", true)
      .append("svg")
      .attr("preserveAspectRatio", "xMinYMin meet")
      .attr("viewBox", "0 0 " + canvas.width + " " + canvas_height)
      .classed("svg-content", true)
      .append('g');

      /*d3.select(html_id)
      .append("svg")
      .attr('width', canvas.width)
      .attr('height', canvas_height)
      //.attr("viewBox", [-canvas.width/2, -canvas_height/2, canvas.width, canvas_height])
      //.attr("style", "max-width: 100%; height: auto; height: intrinsic;");*/





  // ----------------->
  // ----- TITLE ----->
  // ----------------->

  // Group
  var g_title = svg.append('g')
    .attr('class', "g_title")
    .attr('transform', `translate(${margin.left}, ${margin.top})`);


  //  Title Text
  /*if(title.value != null){
      g_title.selectAll('title_text')
          .data(splitWrapText(title.value, (canvas.width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family))
          .enter()
          .append('text')
            .style('font-family', font.family)
            .style('font-size', title.size +  "px")
            .style('font-weight', title.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', 'hanging')
            .attr('class', "title_text")
            .attr('x', margin.left + ((canvas.width - margin.left - margin.right)/2))
            .attr('dy', function(d, i){ return i*1.1 + 'em'})
            .text(d => d);

      if(title.line){
          g_title.append('path')
            .attr('d', 'M' + 0 + ',' + (height.title - (margin.g/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (height.title - (margin.g/2)))
            .attr('stroke', '#d3d2d2')
            .attr('stroke-width', '2')
      }
  }*/

  if(title.value != null){

      title.value.forEach(function(vTitle, iTitle){

        g_title.selectAll('title_text')
            .data(splitWrapText(vTitle.text, (canvas.width - margin.left - margin.right), fontSize=vTitle.size, fontWeight=vTitle.weight, fontFamily=font.family))
            .enter()
            .append('text')
              .style('font-family', font.family)
              .style('font-size', vTitle.size +  "px")
              .style('font-weight', vTitle.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('class', 'title_text_', iTitle)
              .attr('x', margin.left + ((canvas.width - margin.left - margin.right)/2))
              .attr('dy', function(d, i){ return i*1.1 + 'em' })
              .attr('transform', `translate(${0}, ${title_ypos[iTitle]})`)
              .text(d => d);

      })

      if(title.line){
          g_title.append('path')
            .attr('d', 'M' + 0 + ',' + (height.title - (margin.g/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (height.title - (margin.g/2)))
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
    .attr('class', "g_scroll")
    .attr('transform', `translate(${margin.left}, ${margin.top + height.title})`);


  if(scroll.var != null){

    // Scroll Label
    if(scroll.label.value != null){
        g_scroll.selectAll('scroll_title')
            .data(splitWrapText(scroll.label.value, (canvas.width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family))
            .enter()
            .append("text")
              .attr('class', "scroll_title")
              .style('font-family', font.family)
              .style('font-size', scroll.label.size +  "px")
              .style('font-weight', scroll.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('x', (canvas.width - margin.left - margin.right)/2)
              .attr('dy', function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



      var maxScrollWidth = 0;

      domainScroll.forEach(function(vScroll, iScroll){

          var scrollData = splitWrapText(vScroll, (canvas.width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family)

          g_scroll.selectAll('scroll_text')
              .data(scrollData)
              .enter()
              .append("text")
                .attr('class', "scroll_text_" + iScroll)
                .attr('opacity', function(){ return 1 - Math.min(iScroll, 1) })
                .style('font-family', font.family)
                .style('font-size', scroll.size +  "px")
                .style('font-weight', scroll.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('x', (canvas.width - margin.left - margin.right)/2)
                .attr('transform', `translate(${(Math.min(iScroll, 1)*canvas.width)}, ${height.scrollLabel})`)
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .text(d => d);


          scrollData.forEach(function(vScroll2, iScroll2){
            maxScrollWidth = (textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family) > maxScrollWidth)? textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family): maxScrollWidth;
          })
      });


      var scrollIndex = 0;

      g_scroll.append('path')
            .attr('class', "scroll_right")
            .attr('d', 'M' + (canvas.width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas.width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas.width - (margin.left + margin.right))/2)-scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas.width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
            .attr('stroke', "#d3d2d2")
            .attr('fill', "#d3d2d2")
            .attr('transform', `translate(${-((maxScrollWidth/2) + 20)}, ${0})`)
            .on('click', function(event){
              scrollChart('down')
            })
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      g_scroll.append('path')
            .attr('class', "scroll_right")
            .attr('d', 'M' + (canvas.width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas.width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas.width - (margin.left + margin.right))/2)+scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas.width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
            .attr('stroke', "#d3d2d2")
            .attr('fill', "#d3d2d2")
            .attr('transform', `translate(${((maxScrollWidth/2) + 20)}, ${0})`)
            .on('click', function(event){
              scrollChart('up')
            })
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      if(scroll.line){
          g_scroll.append('path')
            .attr('d', 'M' + 0 + ',' + (height.scroll - (margin.g/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (height.scroll - (margin.g/2)))
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
    .attr('class', "g_switcher")
    .attr('transform', `translate(${canvas.width/2}, ${margin.top + height.title + height.scroll})`);

  if(switcher.var != null){

    // Switcher Label
    if(switcher.label.value != null){
        g_switcher.selectAll('switch_title')
            .data(splitWrapText(switcher.label.value, (canvas.width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family))
            .enter()
            .append("text")
              .attr('class', "switcher_title")
              .style('font-family', font.family)
              .style('font-size', switcher.label.size +  "px")
              .style('font-weight', switcher.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('x', 0)
              .attr('dy', function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



    var switcherGroup = g_switcher.selectAll('.switcher')
        .data(switcherText)
        .enter()
        .append("g")
          .attr('class', function(d, i){ return "switcher switcher_" + i})
          .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.switcherLabel)})` })
          .attr('opacity', function(d, i){
            if(i == 0){ return 1.0 }
            else{ return 0.2 }
          })
          .on('click', (event, v) => {

                svg.selectAll('.switcher').attr('opacity', 0.2);
                svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);

                changeLines(event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1] )

          })
          .on('mouseover', function(d) {
              d3.select(this).style("cursor", "pointer");
          });


    switcherGroup.append("rect")
      .attr('class', function(d, i){ return "switcher_" + i})
      .attr('width-value', d => d['width-value'])
      .attr('x', 5)
      .attr('y', -3)
      .attr('width', d => d['width-value']-8)
      .attr('height', d => (d['text'].length*(switcher.size*1.1)) + 6)
      .attr('fill', '#d3d2d2');


    switcherGroup.append("text")
      .attr('class', function(d, i){ return "switcher_" + i})
      .style('font-family', font.family)
      .style('font-size', switcher.size +  "px")
      .style('font-weight', switcher.weight)
      .style('text-anchor', 'middle')
      .style('dominant-baseline', 'hanging')
      .attr('width-value', d => d['width-value'])
      .attr('x', 0)
      .each(function(d, i){
        d3.select(this).selectAll('.switcher_text_' + i)
          .data(d['text'])
          .enter()
          .append('tspan')
          .attr('x', d => d['max-width-value']/2) // Centre-align horizontally
          .attr('dy', d => d['dy'])
          .text( d => d['value'])
      });


    if(switcher.line){
        g_switcher.append('path')
          .attr('d', 'M' + 0 + ',' + (height.switcher - (margin.g/2)) + 'L' + (canvas.width - (margin.left+margin.right)) + ',' + (height.switcher - (margin.g/2)))
          .attr('stroke', '#d3d2d2')
          .attr('stroke-width', '2')
          .attr('transform', function(d){ return `translate(${(-(canvas.width/2)+margin.left)}, ${0})` })

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
    .attr('class', "g_legend")
    .attr('transform', `translate(${canvas.width/2}, ${margin.top + height.title + height.scroll + height.switcher})`);


  if(group.var != null){
      // Legend Label
      if(group.label.value != null){
          g_legend.selectAll('legend_title')
              .data(splitWrapText(group.label.value, (canvas.width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family))
              .enter()
              .append("text")
                .attr('class', "legend_title")
                .style('font-family', font.family)
                .style('font-size', group.label.size +  "px")
                .style('font-weight', group.label.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('x', 0)
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
      }

      var legend = g_legend.selectAll('.legend')
          .data(legendText)
          .enter()
          .append("g")
            .attr('class', function(d, i){ return "legend legend_" + i})
            .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
            .attr('opacity', 1.0)
            .on('dblclick', (event, v) => {

                  svg.selectAll('.legend').attr('opacity', 0.2);
                  svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);

                  svg.selectAll('.group_all').transition().duration(200).attr('visibility', 'hidden');
                  svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('visibility', 'visible');

            })
            .on('click', (event, v) => {

                  if(+event.currentTarget.getAttribute('opacity') == 1){
                      svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 0.2);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]).transition().duration(200).attr('visibility', 'hidden');
                  }
                  else{
                      svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]).transition().duration(200).attr('visibility', 'visible');
                  }

            })
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      legend.append('rect')
        .attr('class', function(d, i){ return "legend_" + i})
        .attr('x', 0)
        .attr('width', group.size)
        .attr('height', group.size)
        .attr('fill', d => d['color']);

      legend.append("text")
        .attr('class', function(d, i){ return "legend_" + i})
        .style('font-family', font.family)
        .style('font-size', group.size +  "px")
        .style('font-weight', group.weight)
        .style('text-anchor', "start")
        .style('dominant-baseline', 'hanging')
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
    .attr('class', function(d, i){ return "g_chart scroll_" + i})
    .attr('opacity', function(d, i){ return 1 - Math.min(i, 1) })
    .attr('x', function(d, i){
      return canvas.width*i
    })
    .attr('transform', function(d, i){
      return `translate(${((canvas.width*Math.min(1, i)) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
    })
    .on('dblclick', (event, v) => {
          // Reset graph to show all items if you double-click the main area
          svg.selectAll('.legend').attr('opacity', 1.0);

          svg.selectAll('.group_all').transition().duration(200).attr('visibility', 'visible');
    });





    // ----- Add Lines to plot ----->
    dataPlot.forEach(function(vScroll, iScroll){

      vScroll.forEach(function(vFacet, iFacet){

        var g_facet = svg.select('.scroll_' + iScroll)
          .append('g')
          .attr('class', 'facet_' + iFacet)
          .attr('transform', `translate(${0}, ${facet_ypos[iScroll][iFacet]})`);



        // ----- Facet Title ----->
        if(facet.var != null){
          g_facet.selectAll('facet_text')
              .data(splitWrapText(domainFacet[iScroll][iFacet]['facet'], (canvas.width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
              .enter()
              .append("text")
                .style('font-family', font.family)
                .style('font-size', facet.size +  "px")
                .style('font-weight', facet.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('class', "facet_text")
                .attr('x', (canvas.width - margin.left - margin.right)/2)
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .attr('transform', `translate(${0}, ${-height.facetLabel[iScroll][iFacet] + facet.space_above_title})`)
                .text(d => d);

        }
        // <----- Facet Title -----





        var g_polar = g_facet
          .append('g')
          .attr('class', 'g_polar')
          .attr('transform', `translate(${margin.left + ((canvas.width - margin.left - margin.right)/2)}, ${yaxis.offset.top + (yaxis.height/2)})`)






        // --- Gray Circle in Background --->
        var g_background = g_polar.append("g")
          .attr('class', 'g_background');


        xTicks.forEach(function(v, i, a){

          g_background.selectAll(".radius_path_" + i)
            .data(data_radius[iScroll][iFacet])
            .enter()
            .append("path")
              .attr('class',  "radius_path_" + i)
              .attr("d", d3.arc().innerRadius((outerRadius*1.0)*(i/a.length)).outerRadius((outerRadius*1.0)*((i+1)/a.length)) )
              .attr('stroke', 'white')
              .attr('stroke-width', '2px')
              .attr('opacity', 0.4)
              .attr('fill', '#d3d2d2') // light gray
        });

        // Labels around edge of circle
        domainFacet[iScroll][iFacet]['y'].forEach(function(v, i, a){

          var g_radius_label = g_background.append("g")
            .attr('class', 'radius_label_' + i);

          var angle = 360*(domainFacet[iScroll][iFacet]['y'].indexOf(v) / domainFacet[iScroll][iFacet]['y'].length);
          var radius = outerRadius*1.01;

          var x = radius * Math.sin(Math.PI * 2 * angle / 360);
          var y = -(radius * Math.cos(Math.PI * 2 * angle / 360));

          var v_split_wrap = splitWrapText(v, yaxis.tick.width, fontSize=yaxis.tick.size, fontWeight=yaxis.tick.weight, fontFamily=font.family)

          v_split_wrap.forEach(function(v2, i2, a2){

            g_radius_label.append('text')
              .attr('x', x)
              .attr('y', y + (((((yaxis.tick.size*1.1)*a2.length))/a2.length)*i2) )
              .style('text-anchor', function(d){
                 if(Math.round(x) == 0){ return 'middle'}
                 else if (x > 0){ return 'start'}
                 else{ return 'end'}
              })
              .style("alignment-baseline", 'hanging')
              .style('font-family', font.family)
              .style('font-size', yaxis.tick.size + "px")
              .style('font-weight', yaxis.tick.weight)
              .text(v2);


          });

          if(angle < 90 || angle > 270){
            g_radius_label.attr('transform', `translate(${0}, ${-((yaxis.tick.size*1.1)*v_split_wrap.length)})`);
          }
          if(Math.round(angle) == 90 || Math.round(angle) == 270){
            g_radius_label.attr('transform', `translate(${0}, ${-(((yaxis.tick.size*1.1)*v_split_wrap.length)/2)})`);
          }

        });

        // <--- Gray Circle in Background ---




        // --- Score range axis across radius of circle --->

        // Add Axis to plot
        if(xaxis.show){
        var x_axis = g_background.append("g")
            .attr('class', "x_axis")
            .style('font-size', xaxis.tick.size + "px")
            .style('font-family', font.family)
            .call(xAxisChart);
          }
        // <--- Score range axis across radius of circle ---





        vFacet.forEach(function(vGroup, iGroup){


          var g_data = g_polar
            .append('g')
              .attr('class', function(d, i){
                return 'group_all group_' + iGroup
              })
              .attr('scroll-value', domainScroll[iScroll])
              .attr('switcher-value', domainSwitcher[0])
              .attr('group-value', domainGroup.map(d => d['group'])[vGroup['data']])
              .attr('opacity', 1.0)



          // ----- Add CI ----->
          if(x.ci.lower != null && x.ci.upper != null){

              g_data.append('path')
                .datum(vGroup[0]['data'])
                  .attr('class', function(d){
                    return 'data_ci_line_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + '0' +
                    ' group_all group_' + iGroup +
                    ' polar_ci_line polar_ci_line_' + html_id.slice(1)
                  })
                  .attr('switcher-value', 0)
                  .attr('fill', vGroup[0]['color'])
                  .attr('stroke', 'none')
                  .attr('stroke-width', 'none')
                  .attr('opacity', d => Math.max(0.1, line.opacity-0.5))
                  .attr('visibility', 'visible')
                  .attr("d", d3.area()
                    .x0(0)
                    .x1(0)
                    .y0(0)
                    .y1(0)
                    .curve(d3.curveLinearClosed)
                  )
                  .transition()
                    .duration(500)
                    .attr("d", d3.area()
                      .x0(d => d['ci_l'])
                      .x1(d => d['ci_u'])
                      .y0(d => d['y_ci_l'])
                      .y1(d => d['y_ci_u'])
                      .curve(d3.curveLinearClosed)
                    )
          }



          // ----- Add Lines ----->
          g_data.append("path")
            .datum(vGroup[0]['data'])
            .attr('class', function(d){
              return 'data_line_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + '0' +
              ' group_all group_' + iGroup +
              ' polar_line'
            })
            .attr('switcher-value', 0)
            .attr('fill', 'none')
            .attr('stroke', vGroup[0]['color'])
            .attr('stroke-width', d => (line.width != null)? line.width: 1.5)
            .attr('opacity', 1)
            .attr('visibility', 'visible')
            .attr("d", d3.line()
              .x(0)
              .y(0)
              .curve(d3.curveLinearClosed)
            )
            .transition()
              .duration(500)
              .attr("d", d3.line()
                .x(d => d['x'])
                .y(d => d['y'])
                .curve(d3.curveLinearClosed)
              )



          // ----- Add Circles ----->
          g_data.selectAll('data_circ').data(vGroup[0]['data'])
            .enter()
            .append("circle")
            .attr('class', function(d, i){
              return 'data_circ_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + '0' + '_' + i +
              ' group_all group_' + iGroup +
              ' polar_circ'
            })
            .attr('x-value', d => d['x'])
            .attr('y-value', d => d['y'])
            .attr('switcher-value', 0)
            .attr('group-value', domainGroup.map(d => d['group'])[iGroup])
            .attr('cx', 0)
            .attr('cy', 0)
            .attr('fill', vGroup[0]['color'])
            .attr('r', d => (line.width != null)? (line.width+1): (1.5+1))
            .attr('opacity', 1)
            .attr('visibility', 'visible')
            .on('mouseover', function(event, d){
              // ----- Tooltip ----->

              if(event.currentTarget.getAttribute('visibility') == 'visible'){

                var thisX = +event.currentTarget.getAttribute('x-value') + (canvas.width/2);
                var thisY = +event.currentTarget.getAttribute('y-value') + (margin.top + height.title + height.scroll + height.switcher + height.legend) + (yaxis.offset.top) + (yaxis.height/2);


                var maxTextWidth = 0;
                var rectHeight = 0;
                var hoverText = [];

                /*
                if(group.var != null){
                  hoverText.push({
                    'value':event.currentTarget.getAttribute('group-value').replace('<br>', ' ').replace('\n', ' '),
                    'size':group.size,
                    'weight':group.weight
                  })

                  rectHeight += (group.size*1.1);
                  maxTextWidth = (textWidth(event.currentTarget.getAttribute('group-value'), group.size, group.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute('group-value'), group.size, group.weight): maxTextWidth;
                }
                */

                var scrollIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[2]
                var facetIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[3]
                var groupIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[4]
                var switcherIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[5]
                var obsIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[6]
                //console.log('scrollIndex', scrollIndex, 'facetIndex', facetIndex, 'groupIndex', groupIndex, 'switcherIndex', switcherIndex, 'obsIndex', obsIndex)

                var dataPoint = dataPlot[scrollIndex][facetIndex][groupIndex][switcherIndex]['data'][obsIndex]
                //console.log('dataPoint:', dataPoint)

                thisY += facet_ypos[facetIndex]

                if(tooltip_text != null){
                  tooltip_text.forEach(function(vTooltipLine, iTooltipLine, aTooltipLine){
                    var val = '';
                    rectHeight += (vTooltipLine.size*1.1);

                    vTooltipLine['text'].forEach(function(vTooltipLineText, iTooltipLineText){
                      val = val.concat(
                        ((vTooltipLineText['prefix'] != null)?vTooltipLineText['prefix']:'') + ((vTooltipLineText['var'] != null)?((vTooltipLineText['format'] != null)? d3.format(vTooltipLineText['format'])(dataPoint[vTooltipLineText['var']]): dataPoint[vTooltipLineText['var']]): '') + ((vTooltipLineText['suffix'] != null)?vTooltipLineText['suffix']:'')
                      )
                    })
                    maxTextWidth = (textWidth(val, vTooltipLine.size, vTooltipLine.weight) > maxTextWidth)? textWidth(val, vTooltipLine.size, vTooltipLine.weight): maxTextWidth;

                    hoverText.push({
                      'value': val.replace('<br>', ' ').replace('\n', ' '),
                      'size': vTooltipLine.size,
                      'weight': vTooltipLine.weight
                    });
                  })
                }

                else{

                  if(group.var != null){
                    hoverText.push({
                      'value':event.currentTarget.getAttribute('group-value').replace('<br>', ' ').replace('\n', ' '),
                      'size':group.size,
                      'weight':group.weight
                    })

                    rectHeight += (group.size*1.1);
                    maxTextWidth = (textWidth(event.currentTarget.getAttribute('group-value'), group.size, group.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute('group-value'), group.size, group.weight): maxTextWidth;
                  }


                  hoverText.push({
                    'value': d3.format((xaxis.format != null)?xaxis.format:'')(dataPoint['x_orig']) + ((xaxis.suffix != null)? xaxis.suffix: ''),
                    'size': yaxis.tick.size,
                    'weight': yaxis.tick.weight
                  });

                  rectHeight += (yaxis.tick.size*1.1);
                  maxTextWidth = Math.max(textWidth(d3.format((xaxis.format != null)?xaxis.format:'')(dataPoint['x_orig']) + ((xaxis.suffix != null)? xaxis.suffix: ''), xaxis.tick.size, xaxis.tick.weight), maxTextWidth)
                }


                if((thisX + (maxTextWidth*0.5) + 5) > (canvas.width - margin.right)){
                  var shift_left = Math.abs((canvas.width - margin.right) - (thisX + (maxTextWidth*0.5) + 5))
                };


                tooltip
                    .style('opacity', 1)
                    .attr('transform', `translate(${(thisX-(shift_left || 0))}, ${(thisY-rectHeight-6)})`)

                tooltipRect.attr('stroke', function(){
                    if(event.currentTarget.getAttribute("color-value") == 'white' || event.currentTarget.getAttribute("color-value") == "rgb(255,255,255)" || event.currentTarget.getAttribute("color-value") == "#fff" || event.currentTarget.getAttribute("color-value") == "#ffffff"){
                      return '#d3d2d2'
                    }
                    else{
                      return event.currentTarget.getAttribute('fill')
                    }
                  })
                  .attr('width', maxTextWidth + 20)
                  .attr('height', rectHeight+6)
                  .attr('x', -((maxTextWidth + 20)*0.5));

                tooltipText.selectAll('tspan').remove();

                var dy = 0;
                hoverText.forEach(function(vHover, iHover){
                  tooltipText.append('tspan')
                      .style('font-size', vHover['size'])
                      .style('font-weight', vHover['weight'])
                      .attr('x', 0)
                      .attr('y', 0)
                      .attr('dy', dy + 'px')
                      .text(vHover['value']);

                  dy += 1.1*vHover['size'];
                })
              }

              // <----- Tooltip -----

            })
            .on('mouseout', function(event, d){
              tooltip.style('opacity', 0).attr('transform', "translate(" + 0 + "," + 0 +")");
            })
            .transition()
              .duration(500)
              .attr('cx', d => d['x'])
              .attr('cy', d => d['y'])



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
    .attr('class', "tooltip_" + html_id.slice(1))
    .style('opacity', 0);

  var tooltipRect =  tooltip.append('rect')
      .attr('class', "tooltip_" + html_id.slice(1) + "__rect")
      .attr('x', 0)
      .attr('y', -3)
      .attr('width', 0)
      .attr('height', 0)
      .attr('fill', "white")
      .attr('stroke', "black")
      .attr('stroke-width', "2");

  var tooltipText = tooltip.append('text')
    .style('text-anchor', 'middle')
    .style('dominant-baseline', 'hanging')
    .attr('class', "tooltip_" + html_id.slice(1) + "__text")
    .style('font-family', font.family)
    .attr('x', 0)
    .attr('y', 0)

  // <-------------------
  // <----- TOOLTIP -----
  // <-------------------





  // ---------------------->
  // ----- Zoom & Pan ----->
  // ---------------------->
  if(zoom){
    let zoomChart = d3.zoom()
      .on('zoom', handleZoom)
      .scaleExtent([0.5, 1])
      .translateExtent([[0, 0], [canvas.width, canvas.height]]);

    function handleZoom(e) {
      d3.select(html_id + ' svg g')
        .attr('transform', e.transform);
    }

    d3.select(html_id + ' svg')
      .call(zoomChart);
  }
  // <----------------------
  // <----- Zoom & Pan -----
  // <----------------------


}

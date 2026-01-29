function chart_line(
  data,
  html_id,

  x={var:null, order:'as_appear', ascending:true},
  y={var:null, ascending:true, ci:{lower:null, upper:null}}, // Must be numeric

  title={value:[{size:40, weight:700, text:null}, {size:32, weight:700, text:null}], line:false},

  clr={
    var:'clr',
    palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
    value:'#e32726'
  }, // Variable containing color of bar(s), a name of a pre-defined palette of colors, or value to set all bars to same color
  line={show_points:true, width:{var:null, value:1}, opacity:{var:null, value:1.0} },

  facet={var:null, size:18, weight:400, space_above_title:5, order:'as_appear', ascending:true, line:{show:false, color:'#d3d2d2'}},
  group={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, show:true},
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
    type:'numeric', //'numeric' or 'category' or 'time'
    label:{value:null, size:20, weight:700},
    offset: {left:10, right:10},
    range:[null, null],
    rangeScroll:'fixed', // 'fixed' or 'free'
    rangeFacet:'fixed', // 'fixed' or 'free'
    suffix:null,
    format:null,
    tick:{size:14, weight:400, orientation:'h', splitWidth:150},
    show:true,
    show_line:true,
    show_ticks:true,
    num_ticks:null,
    show_grid:false
  },

  yaxis={
    height:400,
    label:{value:null, size:20, weight:700},
    offset: {top:10, bottom:10},
    range:[null, null],
    rangeScroll:'fixed', // 'fixed' or 'free'
    rangeFacet:'fixed', // 'fixed' or 'free'
    suffix:null,
    format:null,
    tick:{size:14, weight:400, width:150},
    show:true,
    show_line:true,
    show_ticks:true,
    num_ticks:null,
    show_grid:false
  },

  font={family:body_font},

  margin={top:10, bottom:10, left:10, right:10, g:10},

  canvas={width:960},

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
    'dark24': ['#2E91E5', '#E15F99', '#1CA71C', '#FB0D0D', '#DA16FF', '#222A2A', '#B68100', '#750D86', '#EB663B', '#511CFB', '#00A08B', '#FB00D1', '#FC0080', '#B2828D', '#6C7C32', '#778AAE', '#862A16', '#A777F1', '#620042', '#1616A7', '#DA60CA', '#6C4516', '#0D2A63', '#AF0038'],
    'light24': ['#FD3216', '#00FE35', '#6A76FC', '#FED4C4', '#FE00CE', '#0DF9FF', '#F6F926', '#FF9616', '#479B55', '#EEA6FB', '#DC587D', '#D626FF', '#6E899C', '#00B5F7', '#B68E00', '#C9FBE5', '#FF0092', '#22FFA7', '#E3EE9E', '#86CE00', '#BC7196', '#7E7DCD', '#FC6955', '#E48F72'],
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
        .attr("x", -99999)
        .attr("y", -99999)
        .style('font-family', fontFamily)
        .style('font-size', fontSize + 'px')
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
              if(y.ci.lower != null && y.ci.upper != null){
                svg.select('.scroll_' + iScroll)
                  .select('.facet_' + iFacet)
                  .select('.group_' + iGroup)
                  .selectAll('.chart_ci_line')
                  .datum(vGroup[iSwitch]['data'])
                  .transition()
                    .duration(800)
                    .attr('switcher-value', iSwitch)
                    .attr("d", d3.area()
                      .x(d => d['x'])
                      .y0(d => d['ci_l'])
                      .y1(d => d['ci_u'])
                      .curve(d3.curveLinear)
                    );
              }

              // --- Change Lines --->
              svg.select('.scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .select('.group_' + iGroup)
                .selectAll('.chart_line')
                .datum(vGroup[iSwitch]['data'])
                .transition()
                  .duration(800)
                  .attr('switcher-value', iSwitch)
                  .attr('stroke', vGroup[iSwitch]['color'])
                  .attr('stroke-width', 1.5)
                  .attr("d", d3.line()
                    .x(d => d['x'])
                    .y(d => d['y'])
                    .curve(d3.curveLinear)
                  );



              // --- Change circles --->
              svg.select('.scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .select('.group_' + iGroup)
                .selectAll('.chart_circ')
                .data(vGroup[iSwitch]['data'])
                .transition()
                  .duration(800)
                  .attr('switcher-value', iSwitch)
                  .attr('class', function(d, i){
                    return 'data_circ_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + iSwitch + '_' + i +
                    ' group_all group_' + iGroup +
                    ' chart_circ'
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










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>

  // Scroll domain
  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  if(!scroll.ascending){domainScroll.reverse(); }
  //console.log('### domainScroll', domainScroll);



  // X domain
  /*
  if(xaxis.type == 'category'){
    var domainX = [];
    Array.from(new Set(data.map(d => d[x.var]))).forEach(function(vX, iX){
      domainX.push({
        'x': vX,
        //'color': (clr.var != null)? data.filter(d => d[x.var] == vX).map(d => d[clr.var])[0]: ((clr.value != null)? clr.value: '#e32726')
      })
    })
    if(x.order == 'alphabetical'){ if(x.order == 'alphabetical'){ domainX.sort((a, b) => d3.ascending(a['x'], b['x'])); } }
    if(!x.ascending){ domainX.reverse(); }
  }

  // Get colors for each group
  domainX.forEach(function(v, i){
    if(clr.var != null){
      v['color'] = data.filter(d => d[x.var] == v['x']).map(d => d[clr.var])[0];
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
  //console.log('domainX', domainX);
  */



  // Facet domain
  var domainFacet = []
  domainScroll.forEach(function(vScroll, iScroll){
    domainFacet[iScroll] = []

    if(facet.var != null){
      Array.from(new Set(data.filter(d => (scroll.var != null)? (d[scroll.var] == vScroll): true).map(d => d[facet.var].toString()))).forEach(function(vFacet, iFacet){

        //if(xaxis.type == 'category'){

          if(xaxis.rangeFacet == 'free'){
            if(xaxis.rangeScroll == 'free'){
              var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[x.var].toString())));
            }
            else{
              var facetX = Array.from(new Set(data.filter(d => d[facet.var] == vFacet).map(d => d[x.var].toString())));
            }
          }
          else{
            if(xaxis.rangeScroll == 'free'){
              var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[x.var].toString())));
            }
            else{
              var facetX = Array.from(new Set(data.map(d => d[x.var].toString())));
            }
          }

          if(x.order == 'alphabetical'){ facetX.sort(); }
          if(xaxis.type != 'category'){
            facetX.sort(function(a, b) {
              return a - b;
            });
          }
          if(!x.ascending){ facetX.reverse(); }

        //}
        //else{
        //  var facetX = null;
        //}

        domainFacet[iScroll][iFacet] = {'facet': vFacet, 'x': facetX}
      })
    }
    else{

      if(xaxis.rangeScroll == 'free'){
        if(xaxis.type == 'category'){
          var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[x.var].toString())));
        }
        else{
          var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[x.var])));
        }
      }
      else{
        if(xaxis.type == 'category'){
          var facetX = Array.from(new Set(data.map(d => d[x.var].toString())));
        }
        else{
          var facetX = Array.from(new Set(data.map(d => d[x.var])));
        }
      }

      if(x.order == 'alphabetical'){ facetX.sort(); }
      if(xaxis.type != 'category'){
        var facetX = facetX.map(d => { return parseFloat(d); });
        facetX.sort(function(a, b) {
          return a - b;
        });
      }
      if(!x.ascending){ facetX.reverse(); }

      domainFacet[iScroll][0] = {'facet': null, 'x': facetX}

    }

    if(xaxis.type == 'category'){
      if(facet.order == 'alphabetical'){ domainFacet[iScroll].sort((a, b) => d3.ascending(a['facet'], b['facet'])); }
      if(!facet.ascending){ domainFacet[iScroll].reverse(); }
    }
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
    }];
  }
  if(group.var != null && group.order == 'alphabetical'){
    //domainGroup.sort();
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
    if(group.show == undefined || group.show){

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


      height.legend = maxY + (maxRowInLastLine*(group.size*1.1)) + height.legendLabel + 10;
    }
  }








  // Y-Axis Label Margin
  margin.yaxisLabel = (yaxis.label.value != null)? (yaxis.label.size*1.1)*splitWrapText(yaxis.label.value, yaxis.height, fontSize=yaxis.label.size, fontWeight=yaxis.label.weight, fontFamily=font.family).length + (10) : 0;





  // --- Y-Axis --->

  var yScale = [];
  var yAxisChart = [];
  margin.yaxis = 0;


  domainFacet.forEach(function(vScroll, iScroll){
    yScale[iScroll] = [];
    yAxisChart[iScroll] = [];

    vScroll.forEach(function(vFacet, iFacet){

      // Scale
      var minYvalue = Infinity;
      var maxYvalue = -Infinity;

      if(yaxis.rangeFacet == 'free'){
        if(yaxis.rangeScroll == 'free'){
          data.filter(d => ((scroll.var != null)? (d[scroll.var] == domainScroll[iScroll]): true) && ((facet.var != null)? (d[facet.var] == vFacet['facet']): true)).forEach(function(v, i){
            minYvalue = Math.min(minYvalue, v[y.var]) //(v[y.var] < minYvalue)? v[y.var]: minYvalue;
            maxYvalue = Math.max(maxYvalue, v[y.var]) //(v[y.var] > maxYvalue)? v[y.var]: maxYvalue;
          });
        }
        else{
          data.filter(d => ((facet.var != null)? (d[facet.var] == vFacet['facet']): true)).forEach(function(v, i){
            minYvalue = Math.min(minYvalue, v[y.var]) //(v[y.var] < minYvalue)? v[y.var]: minYvalue;
            maxYvalue = Math.max(maxYvalue, v[y.var]) //(v[y.var] > maxYvalue)? v[y.var]: maxYvalue;
          });
        }
      }
      else{
        if(yaxis.rangeScroll == 'free'){
          data.filter(d => ((scroll.var != null)? (d[scroll.var] == domainScroll[iScroll]): true)).forEach(function(v, i){
            minYvalue = Math.min(minYvalue, v[y.var]) //(v[y.var] < minYvalue)? v[y.var]: minYvalue;
            maxYvalue = Math.max(maxYvalue, v[y.var]) //(v[y.var] > maxYvalue)? v[y.var]: maxYvalue;
          });
        }
        else{
          data.forEach(function(v, i){
            minYvalue = Math.min(minYvalue, v[y.var]) //(v[y.var] < minYvalue)? v[y.var]: minYvalue;
            maxYvalue = Math.max(maxYvalue, v[y.var]) //(v[y.var] > maxYvalue)? v[y.var]: maxYvalue;
          });
        }
      }

      var yScaleDomain = [
        (yaxis.range[1] != null)? yaxis.range[1]: maxYvalue,
        (yaxis.range[0] != null)? yaxis.range[0]: minYvalue
      ]
      if (!y.ascending){ yScaleDomain.reverse() }


      yScale[iScroll][iFacet] = d3.scaleLinear()
      .domain(yScaleDomain)
      .range([
        yaxis.offset.top,
        yaxis.offset.top + yaxis.height
      ]);



      // Axis
      yAxisChart[iScroll][iFacet] = d3.axisLeft(yScale[iScroll][iFacet])
      .tickFormat((d) => (yaxis.suffix != null)? (((yaxis.format) != null? d3.format(yaxis.format)(d): d) + yaxis.suffix): ((yaxis.format) != null? d3.format(yaxis.format)(d): d) );
      //.tickFormat((d) => (yaxis.suffix != null)? (d + yaxis.suffix): d);


      if(yaxis.num_ticks != null){
        yAxisChart[iScroll][iFacet].ticks(yaxis.num_ticks)
      }
      if(xaxis.show_grid){
        yAxisChart[iScroll][iFacet].tickSize(-(xaxis.offset.left + (xScale[iScroll][iFacet].range()[1] - xScale[iScroll][iFacet].range()[0])));
      }


      yAxisChart[iScroll][iFacet].scale().ticks().forEach(function(v, i){
        margin.yaxis = Math.max(margin.yaxis, textWidth(v + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight) + 15 )
      })
    })

  })
  //console.log('margin.yaxis', margin.yaxis)

  // <--- Y-Axis ---


  // --- X-Axis --->

  var xScale = [];
  var xAxisChart = [];
  height.xaxis = []

  if(xaxis.type != 'category'){

    domainFacet.forEach(function(vScroll, iScroll){
      xScale[iScroll] = [];
      xAxisChart[iScroll] = [];
      height.xaxis[iScroll] = [];

      vScroll.forEach(function(vFacet, iFacet){

        // Scale
        var minXvalue = Infinity;
        var maxXvalue = -Infinity;

        if(xaxis.rangeFacet == 'free'){
          if(xaxis.rangeScroll == 'free'){
            data.filter(d => ((scroll.var != null)? (d[scroll.var] == domainScroll[iScroll]): true) && ((facet.var != null)? (d[facet.var] == vFacet['facet']): true)).forEach(function(v, i){
              minXvalue = Math.min(minXvalue, v[x.var]) //(v[x.var] < minXvalue)? v[x.var]: minXvalue;
              maxXvalue = Math.max(maxXvalue, v[x.var]) //(v[x.var] > maxXvalue)? v[x.var]: maxXvalue;
            });
          }
          else{
            data.filter(d => ((facet.var != null)? (d[facet.var] == vFacet['facet']): true)).forEach(function(v, i){
              minXvalue = Math.min(minXvalue, v[x.var]) //(v[x.var] < minXvalue)? v[x.var]: minXvalue;
              maxXvalue = Math.max(maxXvalue, v[x.var]) //(v[x.var] > maxXvalue)? v[x.var]: maxXvalue;
            });
          }
        }
        else{
          if(xaxis.rangeScroll == 'free'){
            data.filter(d => ((scroll.var != null)? (d[scroll.var] == domainScroll[iScroll]): true)).forEach(function(v, i){
              minXvalue = Math.min(minXvalue, v[x.var]) //(v[x.var] < minXvalue)? v[x.var]: minXvalue;
              maxXvalue = Math.max(maxXvalue, v[x.var]) //(v[x.var] > maxXvalue)? v[x.var]: maxXvalue;
            });
          }
          else{
            data.forEach(function(v, i){
              minXvalue = Math.min(minXvalue, v[x.var]) //(v[x.var] < minXvalue)? v[x.var]: minXvalue;
              maxXvalue = Math.max(maxXvalue, v[x.var]) //(v[x.var] > maxXvalue)? v[x.var]: maxXvalue;
            });
          }
        }


        if(xaxis.type == 'time'){
          var xScaleDomain = [
            (xaxis.range[0] != null)? xaxis.range[0]: new Date(minXvalue),
            (xaxis.range[1] != null)? xaxis.range[1]: new Date(maxXvalue)
          ]
        }
        else{
          var xScaleDomain = [
            (xaxis.range[0] != null)? xaxis.range[0]: minXvalue,
            (xaxis.range[1] != null)? xaxis.range[1]: maxXvalue
          ]

        }
        if (!x.ascending){ xScaleDomain.reverse() }





        // Axis
        if(xaxis.type == 'time'){

          xScale[iScroll][iFacet] = d3.scaleTime()
          .domain(xScaleDomain)
          .range([
            margin.yaxisLabel + margin.yaxis + xaxis.offset.left,
            canvas.width - (margin.left + xaxis.offset.right + margin.right)
          ]);

          xAxisChart[iScroll][iFacet] = d3.axisBottom(xScale[iScroll][iFacet]).tickFormat(d3.timeFormat((xaxis.format != null)? xaxis.format: '%d %b %Y'))
          //.ticks(10).map(d3.utcFormat("%I %p"))
        }
        else{

          xScale[iScroll][iFacet] = d3.scaleLinear()
          .domain(xScaleDomain)
          .range([
            margin.yaxisLabel + margin.yaxis + xaxis.offset.left,
            canvas.width - (margin.left + xaxis.offset.right + margin.right)
          ]);

          xAxisChart[iScroll][iFacet] = d3.axisBottom(xScale[iScroll][iFacet])
          .tickFormat((d) => (xaxis.suffix != null)? (((xaxis.format) != null? d3.format(xaxis.format)(d): d) + xaxis.suffix): ((xaxis.format) != null? d3.format(xaxis.format)(d): d) );

        }



        if(xaxis.num_ticks != null){
            xAxisChart[iScroll][iFacet].ticks(xaxis.num_ticks)
        }
        if(xaxis.show_grid){
          xAxisChart[iScroll][iFacet].tickSize(-(yaxis.height + yaxis.offset.bottom));
        }


        // Calculate maximum x-axis height for all facets within all scrolls
        if(xaxis.tick.orientation == 'v'){

          height.xaxis[iScroll][iFacet] = 20;

          xAxisChart[iScroll][iFacet].scale().ticks().forEach(function(vXtick, iXtick){
            if(xaxis.type == 'time'){
              height.xaxis[iScroll][iFacet] = Math.max(
                height.xaxis[iScroll][iFacet],
                20 + textWidth(d3.timeFormat((xaxis.format != null)? xaxis.format: '%d %b %Y')(vXtick), xaxis.tick.size, xaxis.tick.weight, font.family)
              )
            }
            else{
              //height.xaxis[iScroll][iFacet] = Math.max(
              //  height.xaxis[iScroll][iFacet],
              //  20 + textWidth(vXtick, xaxis.tick.size, xaxis.tick.weight, font.family)
              //)

              splitWrapText(vXtick, width=xaxis.tick.splitWidth, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).forEach(function(vXtickSplit, iXtickSplit){
                height.xaxis[iScroll][iFacet] = Math.max(
                  height.xaxis[iScroll][iFacet],
                  20 + textWidth(vXtickSplit, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family)
                )
              })


            }
          })

        }
        else{

          height.xaxis[iScroll][iFacet] = 20 + (xaxis.tick.size*1.1);

        }
      })

    })
  }

  else{

    domainFacet.forEach(function(vScroll, iScroll){
      xScale[iScroll] = [];
      xAxisChart[iScroll] = [];
      height.xaxis[iScroll] = [];

      vScroll.forEach(function(vFacet, iFacet){

        xScale[iScroll][iFacet] = d3.scaleBand()
          .domain(vFacet['x'])
          .range([
            margin.yaxisLabel + margin.yaxis + xaxis.offset.left,
            canvas.width - (margin.left + xaxis.offset.right + margin.right)
          ])
          .padding([0.10]);

        xAxisChart[iScroll][iFacet] = d3.axisBottom(xScale[iScroll][iFacet]);

        if(xaxis.show_grid){
          xAxisChart[iScroll][iFacet].tickSize(-(yaxis.height + yaxis.offset.bottom));
        }

        // Calculate maximum x-axis height for all facets within all scrolls
        height.xaxis[iScroll][iFacet] = 0;
        vFacet['x'].forEach(function(vX, iX){

          yAxisChart[iScroll][iFacet].scale().ticks().forEach(function(v, i){
            margin.yaxis = Math.max(margin.yaxis, textWidth(v + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight) + 15)
          })

          if(xaxis.tick.orientation == 'v'){

            var currentX_tick_maxWidth = 0;

            splitWrapText(vX, xaxis.tick.splitWidth, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).forEach(function(vXtick, iXtick){

                currentX_tick_maxWidth = Math.max(
                  currentX_tick_maxWidth,
                  textWidth(vXtick, xaxis.tick.size, xaxis.tick.weight, font.family)
                )

            })

            height.xaxis[iScroll][iFacet] = Math.max(
              height.xaxis[iScroll][iFacet],
              20 + currentX_tick_maxWidth
            )

          }

          else{
            height.xaxis[iScroll][iFacet] = Math.max(
              height.xaxis[iScroll][iFacet],
              20 + (xaxis.tick.size*1.1)*splitWrapText(vX, xScale[iScroll][iFacet].bandwidth()*0.95, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).length
            )
          }

        })

      })
    })

  }

  //console.log('height.xaxis:', height.xaxis)
  // <--- X-Axis ---




  // X-Axis Label Height
  height.xaxisLabel = (xaxis.label.value != null)? (xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, canvas.width - (margin.left + margin.yaxisLabel + margin.yaxis + margin.right), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length + (10) : 0;
  //console.log('height.xaxisLabel:', height.xaxisLabel)






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

      facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + yaxis.height + yaxis.offset.bottom + height.xaxis[iScroll][iFacet];

    })

    height.facet[iScroll] += d3.sum(height.facetLabel[iScroll]);
  })
  //console.log('height.facet:', height.facet)
  //console.log('height.facetLabel:', height.facetLabel)
  //console.log('facet_ypos:', facet_ypos)



  var maxFacets = 0
  domainFacet.forEach(function(vScroll, iScroll){
    maxFacets = Math.max(maxFacets, vScroll.length)
  })

  height.yaxis = (yaxis.height*maxFacets);



  // Calculate height of each Scroll
  height.scrollFace = []
  height.facet.forEach(function(vScroll, iScroll){

    // Height of FACET LABELS + ((yaxis.offset.top + yaxis.height + yaxis.offset.bottom)*No. Facets) + d3.sum(x-axis heights)
    height.scrollFace[iScroll] = d3.sum(height.facetLabel[iScroll]) + ((yaxis.offset.top + yaxis.height + yaxis.offset.bottom)*height.facetLabel[iScroll].length) + vScroll + d3.sum(height.xaxis[iScroll])

  })
  //console.log('height.scrollFace:', height.scrollFace)




  var canvas_height = margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace) + height.xaxisLabel + margin.bottom;

  /*console.log('margin.top', margin.top)
  console.log('height.title', height.title)
  console.log('height.scroll', height.scroll)
  console.log('height.switcher', height.switcher)
  console.log('height.legend', height.legend)
  console.log('d3.max(height.scrollFace)', d3.max(height.scrollFace))
  console.log('height.xaxisLabel', height.xaxisLabel)
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

          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['group'] = (group.var != null)? vGroup['group']: null;
          //dataPlot[iScroll][iFacet][iGroup][iSwitcher]['color'] = (clr.var != null)? ((group.var != null)? domainGroup[iGroup]['color']: ((clr.value != null)? clr.value: '#e32726')): ((clr.value != null)? clr.value: '#e32726');
          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['color'] = (clr.var != null || clr.palette != null)? ((group.var != null)? domainGroup[iGroup]['color']: (dataSlice.map(d => d[clr.var])[0])): ((clr.value != null)? clr.value: '#e32726');
          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['width'] = (line.width.var != null)? dataSlice.map(d => d[line.width.var])[0]: ((line.width.value != null)? line.width.value: 1)
          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['opacity'] = (line.opacity.var != null)? dataSlice.map(d => d[line.opacity.var])[0]: ((line.opacity.value != null)? line.opacity.value: 1)
          dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'] = [];

          if(dataSlice.length > 0){

            vFacet['x'].forEach(function(vX, iX){
              var dataObs = dataSlice.filter(d => d[x.var] == vX)[0]

              var newObs = {
                'x': (dataObs != null)? ((xaxis.type == 'category')? (xScale[iScroll][iFacet](dataObs[x.var]) + (xScale[iScroll][iFacet].bandwidth()*0.5)): xScale[iScroll][iFacet](dataObs[x.var])): null,
                'y': (dataObs != null)? ((dataObs[y.var] != null)? yScale[iScroll][iFacet](dataObs[y.var]): null): null,
                'x_orig': (dataObs != null)? dataObs[x.var]: null,
                'y_orig': (dataObs != null)? dataObs[y.var]: null,
                'group': (group.var != null)? vGroup['group']: null,

                // Confidence Interval Lines
                'ci_l': (y.ci.lower != null && dataObs != null)? yScale[iScroll][iFacet](dataObs[y.ci.lower]): (dataObs != null)? yScale[iScroll][iFacet](dataObs[y.var]):null,
                'ci_u': (y.ci.upper != null && dataObs != null)? yScale[iScroll][iFacet](dataObs[y.ci.upper]): (dataObs != null)? yScale[iScroll][iFacet](dataObs[y.var]):null,

                'ci_l_orig': (y.ci.lower != null && dataObs != null)? dataObs[y.ci.lower]: (dataObs != null)? dataObs[y.var]:null,
                'ci_u_orig': (y.ci.upper != null && dataObs != null)? dataObs[y.ci.upper]: (dataObs != null)? dataObs[y.var]:null
              }


              if(tooltip_text != null){
                tooltip_text.forEach((v, i) => {
                    v['text'].forEach((v2, i2) => {
                      newObs[v2['var']] = (dataObs)?dataObs[v2['var']]: null
                    })
                });
              }

              dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].push(newObs)

            })


            // --- Forward fill observations --->
            var prevX = null;
            var prevY = null;
            var prevX_orig = null;
            var prevY_orig = null;

            dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].forEach(function(v, i){
              if (i == 0){
                prevX = null;
                prevY = null;
                prevX_orig = null;
                prevY_orig = null;
              }


              if (i > 0){
                v['x'] = (v['x'] == null)? prevX: v['x'];
                v['y'] = (v['y'] == null)? prevY: v['y'];
                v['x_orig'] = (v['x_orig'] == null)? prevX_orig: v['x_orig'];
                v['y_orig'] = (v['y_orig'] == null)? prevY_orig: v['y_orig'];
              }

              prevX = v['x'];
              prevY = v['y'];
              prevX_orig = v['x_orig'];
              prevY_orig = v['y_orig'];
            })
            // <--- Forward fill observations ---



            // --- Reverse fill observations --->
            var prevX = null;
            var prevY = null;
            var prevX_orig = null;
            var prevY_orig = null;

            dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].reverse().forEach(function(v, i){
              if (i == 0){
                prevX = null;
                prevY = null;
                prevX_orig = null;
                prevY_orig = null;
              }


              if (i > 0){
                v['x'] = (v['x'] == null)? prevX: v['x'];
                v['y'] = (v['y'] == null)? prevY: v['y'];
                v['x_orig'] = (v['x_orig'] == null)? prevX_orig: v['x_orig'];
                v['y_orig'] = (v['y_orig'] == null)? prevY_orig: v['y_orig'];
              }

              prevX = v['x'];
              prevY = v['y'];
              prevX_orig = v['x_orig'];
              prevY_orig = v['y_orig'];
            })


            dataPlot[iScroll][iFacet][iGroup][iSwitcher]['data'].reverse()
            // <--- Reverse fill observations ---

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
    .style("height", (canvas_height + 10) + 'px') ;*/

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
      .attr("width", canvas.width)
      .attr("height", canvas_height)
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
            .style('font-size', title.size +  'px')
            .style('font-weight', title.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', "hanging")
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
              .style('font-size', vTitle.size +  'px')
              .style('font-weight', vTitle.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', "hanging")
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
  var g_scroll = svg.append('g')
    .attr('class', "g_scroll")
    .attr('transform', `translate(${margin.left}, ${margin.top + height.title})`);


  if(scroll.var != null){

    // Scroll Label
    if(scroll.label.value != null){
        g_scroll.selectAll('scroll_title')
            .data(splitWrapText(scroll.label.value, (canvas.width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family))
            .enter()
            .append('text')
              .attr('class', "scroll_title")
              .style('font-family', font.family)
              .style('font-size', scroll.label.size +  'px')
              .style('font-weight', scroll.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', "hanging")
              .attr('x', (canvas.width - margin.left - margin.right)/2)
              .attr("dy", function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



      var maxScrollWidth = 0;

      domainScroll.forEach(function(vScroll, iScroll){

          var scrollData = splitWrapText(vScroll, (canvas.width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family)

          g_scroll.selectAll('scroll_text')
              .data(scrollData)
              .enter()
              .append('text')
                .attr('class', "scroll_text_" + iScroll)
                .attr('opacity', function(){ return 1 - Math.min(iScroll, 1) })
                .style('font-family', font.family)
                .style('font-size', scroll.size +  'px')
                .style('font-weight', scroll.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', "hanging")
                .attr('x', (canvas.width - margin.left - margin.right)/2)
                .attr('transform', `translate(${(Math.min(iScroll, 1)*canvas.width)}, ${height.scrollLabel})`)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
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
            .on("mouseover", function(d) {
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
            .on("mouseover", function(d) {
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
  var g_switcher = svg.append('g')
    .attr('class', "g_switcher")
    .attr('transform', `translate(${canvas.width/2}, ${margin.top + height.title + height.scroll})`);

  if(switcher.var != null){

    // Switcher Label
    if(switcher.label.value != null){
        g_switcher.selectAll('switch_title')
            .data(splitWrapText(switcher.label.value, (canvas.width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family))
            .enter()
            .append('text')
              .attr('class', "switcher_title")
              .style('font-family', font.family)
              .style('font-size', switcher.label.size +  'px')
              .style('font-weight', switcher.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', "hanging")
              .attr('x', 0)
              .attr("dy", function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



    var switcherGroup = g_switcher.selectAll('.switcher')
        .data(switcherText)
        .enter()
        .append('g')
          .attr('class', function(d, i){ return "switcher switcher_" + i})
          .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.switcherLabel)})` })
          .attr('opacity', function(d, i){
            if(i == 0){ return 1.0 }
            else{ return 0.2 }
          })
          .on('click', (event, v) => {

                svg.selectAll('.switcher').attr('opacity', 0.2);
                svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);

                svg.selectAll('.mouse-area').attr('switcher-value', event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]);

                changeLines(event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1] )

          })
          .on("mouseover", function(d) {
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


    switcherGroup.append('text')
      .attr('class', function(d, i){ return "switcher_" + i})
      .style('font-family', font.family)
      .style('font-size', switcher.size +  'px')
      .style('font-weight', switcher.weight)
      .style('text-anchor', 'middle')
      .style('dominant-baseline', "hanging")
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
  var g_legend = svg.append('g')
    .attr('class', "g_legend")
    .attr('transform', `translate(${canvas.width/2}, ${margin.top + height.title + height.scroll + height.switcher})`);


  if(group.var != null && (group.show == undefined || group.show)){
      // Legend Label
      if(group.label.value != null){
          g_legend.selectAll('legend_title')
              .data(splitWrapText(group.label.value, (canvas.width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .attr('class', "legend_title")
                .style('font-family', font.family)
                .style('font-size', group.label.size +  'px')
                .style('font-weight', group.label.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', "hanging")
                .attr('x', 0)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
      }

      var legend = g_legend.selectAll('.legend')
          .data(legendText)
          .enter()
          .append('g')
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
                  /*
                  if(+event.currentTarget.getAttribute('opacity') == 1){
                      svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 0.2);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('opacity', 0);
                  }
                  else{
                      svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 1.0);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('opacity', 1);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).selectAll('.chart_ci_line').transition().duration(200).attr('opacity', 0.5);
                  }
                  */

                  if(+event.currentTarget.getAttribute('opacity') == 1){
                      svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 0.2);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]).transition().duration(200).attr('visibility', 'hidden');
                  }
                  else{
                      svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]).transition().duration(200).attr('visibility', 'visible');

                  }

            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      legend.append('rect')
        .attr('class', function(d, i){ return "legend_" + i})
        .attr('x', 0)
        .attr('width', group.size)
        .attr('height', group.size)
        .attr('fill', d => d['color']);

      legend.append('text')
        .attr('class', function(d, i){ return "legend_" + i})
        .style('font-family', font.family)
        .style('font-size', group.size +  'px')
        .style('font-weight', group.weight)
        .style('text-anchor', "start")
        .style('dominant-baseline', "hanging")
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
    .append('g')
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



  // ----- Add X-Axis Label to plot ----->
  /*if(xaxis.label.value != null){

      g_chart.append('text')
        .attr('class', "xaxis.label.value")
        .style('font-family', font.family)
        .style('font-size', xaxis.label.size + 'px')
        .style('font-weight', xaxis.label.weight)
        .style('text-anchor', 'middle')
        .style('dominant-baseline', "hanging")
        .attr('x', (margin.yaxisLabel + margin.yaxis + xaxis.offset.left) + (((canvas.width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxisLabel + margin.yaxis + xaxis.offset.left))*0.5) )
        .attr("y", canvas_height - (margin.top + height.title + height.scroll + height.switcher + height.legend + height.xaxisLabel + margin.bottom) + 5)
        .text(xaxis.label.value)
        .call(splitWrapTextSpan, ((canvas.width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxisLabel + margin.yaxis + xaxis.offset.left)), xaxis.label.size, xaxis.label.weight, font.family, valign='middle', dy_extra=0);

  }*/







  // ----- Add Lines to plot ----->
  dataPlot.forEach(function(vScroll, iScroll){

    // ----- Group ----->
    var g_scroll = svg.append('g')
      .attr('class', "g_chart g_scroll_" + iScroll)
      .attr('opacity', d => 1 - Math.min(iScroll, 1))
      .attr('x', canvas.width*iScroll)
      .attr('transform', function(d, i){
        return `translate(${((canvas.width*Math.min(1, iScroll)) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
      });
    // <----- Group -----

    vScroll.forEach(function(vFacet, iFacet){

        var g_facet = g_scroll //svg.select('.scroll_' + iScroll)
          .append('g')
          .attr('class', 'facet_' + iFacet)
          .attr('transform', `translate(${0}, ${facet_ypos[iScroll][iFacet]})`);


        // ----- Add line above Facet ----->
        if(facet.line.show){
          g_facet.append('path')
            .attr('d', 'M' + 0 + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)))
            .attr('stroke', (facet.line.color != null)? facet.line.color: 'black')
            .attr('stroke-width', '2')
        }



        // ----- Facet Title ----->
        if(facet.var != null){
          g_facet.selectAll('facet_text')
              .data(splitWrapText(domainFacet[iScroll][iFacet]['facet'], (canvas.width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .style('font-family', font.family)
                .style('font-size', facet.size +  'px')
                .style('font-weight', facet.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', "hanging")
                .attr('class', "facet_text")
                .attr('x', (canvas.width - margin.left - margin.right)/2)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .attr('transform', `translate(${0}, ${-height.facetLabel[iScroll][iFacet] + facet.space_above_title})`)
                .text(d => d);

        }
        // <----- Facet Title -----




        // ----- Add Y-Axis Label to plot ----->
        if(yaxis.label.value != null){
            g_facet.append('text')
              .style('font-family', font.family)
              .style('font-size', yaxis.label.size + 'px')
              .style('font-weight', yaxis.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', "hanging")
              .attr('x', -(yScale[iScroll][iFacet].range()[0] + ((yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0])*0.5)) ) // Moves vertically (due to rotation)
              .attr("y", 0) // Moves horizontally (due to rotation)
              .attr('transform', "rotate(-90)")
              .text(yaxis.label.value)
              .call(splitWrapTextSpan, height.yaxis, yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
        }
        // <----- Add Y-Axis Label to plot -----





        // ----- Add Y-Axis to plot ----->
        if(yaxis.show){

          if(yaxis.show_grid){

            var maxXrange = xScale[iScroll][iFacet].range()[1] - xScale[iScroll][iFacet].range()[0];
            yAxisChart[iScroll][iFacet].tickSize(-(maxXrange + xaxis.offset.left));

          }

          var y_axis_chart = g_facet.append('g')
              .attr('class', "y_axis")
              .style('font-size', yaxis.tick.size + 'px')
              .attr('transform', "translate(" + (margin.yaxisLabel+margin.yaxis) + "," + 0 + ")")
              .call(yAxisChart[iScroll][iFacet]);


          y_axis_chart.selectAll(".tick text")
              .attr("y", '0.0')
              .call(splitWrapTextSpan, ((canvas.width*0.4) - (margin.left + margin.yaxisLabel)), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);

          // Remove Axis Line
          if(!yaxis.show_line){
            y_axis_chart.select(".domain").remove();
          }

          // Remove Axis Ticks
          if(!yaxis.show_ticks){
            y_axis_chart.selectAll(".tick").selectAll("line").remove();
          }

          if(yaxis.show_grid){
            y_axis_chart.selectAll(".tick line").attr('stroke', "#d3d2d2");
          }

        }
        // <----- Add Y-Axis to plot -----





        // ----- Add X-Axis to plot ----->

        if(xaxis.show){
          var x_axis_chart = g_facet.append('g')
              .attr('class', "x_axis_" + iFacet)
              .style('font-size', xaxis.tick.size + 'px')
              .attr('transform', "translate(" + 0 + "," + (yaxis.offset.top + yaxis.height + yaxis.offset.bottom) + ")")
              .call(xAxisChart[iScroll][iFacet]);

          if(xaxis.type == 'category'){
            //x_axis_chart.selectAll(".tick text")
            //    .attr("x", '0.0')
            //    .call(splitWrapTextSpan, xScale[iScroll][iFacet].bandwidth()*0.95, xaxis.tick.size, xaxis.tick.weight, font.family, valign='bottom', dy_extra=0.7);

            x_axis_chart.selectAll(".tick text")
                .attr('x', '0.0')
                .call(splitWrapTextSpan, (xaxis.tick.orientation == 'h')? xScale[iScroll][iFacet].bandwidth()*0.95: xaxis.tick.splitWidth, xaxis.tick.size, xaxis.tick.weight, font.family, valign='bottom', dy_extra=0.7);

          }

          // --- Tick rotation --->
          if(xaxis.tick.orientation == 'v'){

            x_axis_chart.selectAll('text')
            .style('text-anchor', 'end')
            .attr("transform", "rotate(-90)");

            if(xaxis.type == 'category'){
              x_axis_chart.selectAll('text').selectAll('tspan')
              .attr('dx', "-.8em")
              //.attr('dy', d => parseFloat('0.2em') - 1.1 + 'em');

              x_axis_chart.selectAll('text').selectAll('tspan').each((d,i,nodes) => {
                  nodes[i].setAttribute("dy", parseFloat(nodes[i].getAttribute('dy')) - (0.55 + ((1.1*nodes.length)/2)) + 'em');
              });

              /*var x_dy = x_axis_chart.selectAll('text').selectAll('tspan');
              console.log('x_dy', x_dy)
              x_dy.forEach(function(d,i){
                var old_dy = parseFloat(d.getAttribute("dy"));
                console.log('i', i, 'old_dy', old_dy)
                d3.select(d).transition().attr("dy", function(i){ return old_dy - (0.7 + 1.1) + 'em' ;});
              });*/
            }
            else{
              x_axis_chart.selectAll('text')
              .attr('dx', "-.8em")
              .attr('dy', "-0.55em");
            }

          }
          // <--- Tick rotation ---


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



        // ----- Add X-Axis Label to plot ----->
        if(xaxis.label.value != null && (iFacet+1) == domainFacet[iScroll].length){
            g_facet.append('text')
              .attr('class', 'xaxis_label')
              .style('font-family', font.family)
              .style('font-size', xaxis.label.size + 'px')
              .style('font-weight', xaxis.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('x', xScale[iScroll][0].range()[0] + ((xScale[iScroll][0].range()[1] - xScale[iScroll][0].range()[0])*0.5) )
              .attr('y', yaxis.offset.top + yaxis.height + yaxis.offset.bottom + height.xaxis[iScroll][iFacet] )
              .text(xaxis.label.value)
              .call(splitWrapTextSpan, (xScale[iScroll][0].range()[1] - xScale[iScroll][0].range()[0]), xaxis.label.size, xaxis.label.weight, font.family, valign='bottom', dy_extra=0);
        }
        // <----- Add X-Axis Label to plot -----








        vFacet.forEach(function(vGroup, iGroup){


          var g_data = g_facet
            .append('g')
              .attr('class', function(d, i){
                return 'group_all group_' + iGroup
              })
              .attr('scroll-value', domainScroll[iScroll])
              .attr('switcher-value', domainSwitcher[0])
              .attr('group-value', domainGroup.map(d => d['group'])[vGroup['data']])
              .attr('opacity', 1.0)



          // ----- Add CI ----->
          if(y.ci.lower != null && y.ci.upper != null){

              g_data.append('path')
                .datum(vGroup[0]['data'])
                  .attr('class', function(d){
                    return 'data_ci_line_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + '0' +
                    ' group_all group_' + iGroup +
                    ' chart_ci_line chart_ci_line_' + html_id.slice(1)
                  })
                  .attr('switcher-value', 0)
                  .attr('fill', vGroup[0]['color'])
                  .attr('stroke', 'none')
                  .attr('stroke-width', 'none')
                  .attr("opacity", d => Math.max(0.1, vGroup[0]['opacity']-0.5))
                  .attr('visibility', 'visible')
                  .attr("d", d3.area()
                    .x(0)
                    .y0(0)
                    .y1(0)
                    .curve(d3.curveLinear)
                  )
                  .transition()
                    .duration(500)
                    .attr("d", d3.area()
                      .x(d => d['x'])
                      .y0(d => d['ci_l'])
                      .y1(d => d['ci_u'])
                      .curve(d3.curveLinear)
                    )


          }



          // ----- Add Lines ----->
          g_data.append("path")
            .datum(vGroup[0]['data'])
            .attr('class', function(d){
              return 'data_line_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + '0' +
              ' group_all group_' + iGroup +
              ' chart_line chart_line_' + html_id.slice(1)
            })
            .attr('switcher-value', 0)
            .attr('fill', 'none')
            .attr('stroke', vGroup[0]['color'])
            .attr('stroke-width', vGroup[0]['width'])
            .attr("opacity", vGroup[0]['opacity'])
            .attr('visibility', 'visible')
            .attr("d", d3.line()
              .x(0)
              .y(0)
              .curve(d3.curveLinear)
            )
            .transition()
              .duration(500)
              .attr("d", d3.line()
                .x(d => d['x'])
                .y(d => d['y'])
                .curve(d3.curveLinear)
              )



          // ----- Add Circles ----->
          if(line.show_points){
              g_data.selectAll('data_circ').data(vGroup[0]['data'])
                .enter()
                .append('circle')
                .attr('class', function(d, i){
                  return 'data_circ_' + iScroll + '_' + iFacet + '_' + iGroup + '_' + '0' + '_' + i +
                  ' group_all group_' + iGroup +
                  ' chart_circ'
                })
                .attr('x-value', d => d['x'])
                .attr('y-value', d => d['y'])
                .attr('switcher-value', 0)
                .attr('group-value', domainGroup.map(d => d['group'])[iGroup])
                .attr('cx', 0)
                .attr('cy', 0)
                .attr('fill', vGroup[0]['color'])
                .attr('r', vGroup[0]['width']+1)
                .attr('opacity', 1)
                .attr('visibility', 'visible')
                .transition()
                  .duration(500)
                  .attr('cx', d => d['x'])
                  .attr('cy', d => d['y'])
          }


        });








        // ----------------------------->
        // ---- Mouse-Over Effects ----->
        // ----------------------------->

        var g_mouse = g_facet.append('g')
          .attr('class', "mouse-over-effects")
          .attr('transform', `translate(${(margin.yaxisLabel + margin.yaxis + xaxis.offset.left)}, ${(yaxis.offset.top)})`);


        // --- Black dashed vertical line that follows mouse along X-axis --->
        g_mouse.append("path")
          .attr('class', "mouse-line_" + iScroll + '_' + iFacet)
          .style('stroke', "black")
          .style('stroke-width', "1px")
          .style("stroke-dasharray", ("3, 3"))
          //.attr('opacity', "0")
          .attr('visibility', 'hidden');
        // <--- Black dashed vertical line that follows mouse along X-axis ---




        // --- Tooltip Text for X-axis value --->
        var mouseXaxis = g_mouse.append('g')
          .attr('class', "mouse-xaxis_" + iScroll + '_' + iFacet)
          //.attr('opacity', "0");
          .attr('visibility', 'hidden');


        mouseXaxis.append('rect')
              .attr('class', "mouse-xaxis-rect mouse-xaxis-rect_" + iScroll + '_' + iFacet)
              .attr('x', -10)
              .attr('y', 8) //-(((xaxis.tick.size*1.1)+6)/2))
              .attr('width', 20)
              .attr('height', (xaxis.tick.size*1.1)+6)
              .attr('fill', "white")
              .attr('stroke', 'black')
              .attr('stroke-width', "2");

        mouseXaxis.append('text')
              .attr('class', "mouse-xaxis-text mouse-xaxis-text_" + iScroll + '_' + iFacet)
              .style('stroke', 'black')
              .style('font-family', font.family)
              .style('font-size', xaxis.tick.size +  'px')
              .style('font-weight', xaxis.tick.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', "hanging")
              .attr('transform', "translate(0,11)");
        // <--- Tooltip Text for X-axis value ---



        // --- Tooltip Text for Y-axis values for each Line --->
        var mousePerLine = g_mouse.selectAll('.mouse-per-line')
        .data(domainGroup)
        .enter()
        .append('g')
          //.attr('opacity', "0")
          .attr('visibility', 'hidden')
          .attr('class', function(d, i){ return "mouse-per-line" +
            " mouse-per-line_" + iScroll + '_' + iFacet +
            " mouse-per-line_" + iScroll + '_' + iFacet + '_' + i
          });

        mousePerLine.append('rect')
              .attr('class', function(d, i){ return "mouse-rect mouse-rect_" + iScroll + '_' + iFacet + '_' + i})
              .attr('x', 0)
              .attr('y', -3)
              .attr('width', 0)
              .attr('height', 0)
              //.attr('x', 7)
              //.attr('y', -(((yaxis.tick.size*1.1)+6)/2))
              //.attr('width', 20)
              //.attr('height', (yaxis.tick.size*1.1)+6)
              .attr('fill', "white")
              .attr('stroke', d => d['color'])
              .attr('stroke-width', "2");

        mousePerLine.append('circle')
            .attr('class', function(d, i){ return "mouse-circ mouse-circ_" + iScroll + '_' + iFacet + '_' + i})
            .attr('r', function(d, i){ return vFacet[i][0]['width']+3 })
            .style('stroke', d => d['color'])
            .style('fill', "none")
            .style('stroke-width', "1px")
            .attr('cx', 0)
            .attr('cy', 0);


        mousePerLine.append('text')
        .attr('class', function(d, i){ return "mouse-text mouse-text_" + iScroll + '_' + iFacet + '_' + i})
        .style('stroke', d => d['color'])
        .style('fill', d => d['color'])
        .style('font-family', font.family)
        .style('font-size', yaxis.tick.size +  'px')
        .style('font-weight', yaxis.tick.weight)
        .style('text-anchor', 'middle')
        .style('dominant-baseline', 'hanging')
        .attr('x', 0)
        .attr('y', 0)
        //.attr('transform', "translate(10,2)");
        // <--- Tooltip Text for Y-axis values for each Line ---



        // --- Add hover area for Tooltip texts --->
        g_mouse.append('svg:rect') // append a rect to catch mouse movements on canvas
          .attr('class', 'mouse-area mouse-area_' + iScroll + '_' + iFacet + '_' + 0)
          .attr('switcher-value', 0)
          .attr('width', (xScale[iScroll][iFacet].range()[1] - xScale[iScroll][iFacet].range()[0])) // can't catch mouse events on a g element
          .attr('height', (yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0]) + yaxis.offset.bottom)
          .attr('fill', 'none')
          .attr('pointer-events', 'all')
          .on('mouseout', function() { // on mouse out hide line, circles and text
            svg.selectAll(".mouse-line_" + iScroll + '_' + iFacet)
              //.attr('opacity', "0");
              .attr('visibility', 'hidden');

            svg.selectAll(".mouse-xaxis_" + iScroll + '_' + iFacet)
            //.attr('opacity', "0");
            .attr('visibility', 'hidden');

            svg.selectAll(".mouse-per-line_" + iScroll + '_' + iFacet)
            //.attr('opacity', "0");
            .attr('visibility', 'hidden');
          })
          .on('mouseover', function() { // on mouse in show line, circles and text
            svg.selectAll(".mouse-line_" + iScroll + '_' + iFacet)
            //.attr('opacity', "1");
            .attr('visibility', 'visible');

            // Only show x-axis tooltip for numeric/time axes
            if(xaxis.type != 'category'){
                svg.selectAll(".mouse-xaxis_" + iScroll + '_' + iFacet)
                //.attr('opacity', "1");
                .attr('visibility', 'visible');
            }

            // Only show for legend items that are not hidden
            if(group.var != null && (group.show == undefined || group.show)){
              domainGroup.forEach(function(vGroup, iGroup){
                if(svg.select(".legend_" + iGroup).attr('opacity') == 1){
                  svg.selectAll(".mouse-per-line_" + iScroll + '_' + iFacet + '_' + iGroup)
                  //.attr('opacity', "1");
                  .attr('visibility', 'visible');
                }
              })
            }
            else{
              svg.selectAll(".mouse-per-line_" + iScroll + '_' + iFacet)
              //.attr('opacity', "1");
              .attr('visibility', 'visible');
            }

          })
          .on('mousemove', function() { // mouse moving over canvas
                var mouse = d3.pointer(event);

                var scrollIndex = event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]
                var facetIndex = event.currentTarget.getAttribute('class').split(' ')[1].split('_')[2]
                var switcherIndex = event.currentTarget.getAttribute("switcher-value")

                var diff = Infinity, x_val = null, x_axis_val = Infinity;

                domainFacet[scrollIndex][facetIndex]['x'].forEach(function(vX, iX){
                  if(Math.abs(xScale[scrollIndex][facetIndex](vX) - (mouse[0]+margin.yaxisLabel+margin.yaxis+xaxis.offset.left)) < diff){
                    diff = Math.abs(xScale[scrollIndex][facetIndex](vX) - (mouse[0]+margin.yaxisLabel+margin.yaxis+xaxis.offset.left))
                    x_val = vX
                    x_axis_val = xScale[scrollIndex][facetIndex](vX)
                  }
                })

                g_mouse.select(".mouse-line_" + scrollIndex + '_' + facetIndex)
                  .attr("d", function() {
                    var d = "M" + (x_axis_val - (margin.yaxisLabel+margin.yaxis+xaxis.offset.left) + ((xaxis.type == 'category')? (xScale[scrollIndex][facetIndex].bandwidth()/2): 0)) + "," + ((yScale[scrollIndex][facetIndex].range()[1] - yScale[scrollIndex][facetIndex].range()[0]) + yaxis.offset.bottom); //(canvas_height - (margin.top + height.title));
                    d += " " + (x_axis_val - (margin.yaxisLabel+margin.yaxis+xaxis.offset.left) + ((xaxis.type == 'category')? (xScale[scrollIndex][facetIndex].bandwidth()/2): 0)) + "," + 0;
                    return d;
                  });


                // --- X-axis Tooltip --->
                g_mouse.select(".mouse-xaxis_" + scrollIndex + '_' + facetIndex)
                  .attr('transform', "translate(" + (x_axis_val - (margin.yaxisLabel+margin.yaxis+xaxis.offset.left) + ((xaxis.type == 'category')? (xScale[scrollIndex][facetIndex].bandwidth()/2): 0)) + "," + (yScale[scrollIndex][facetIndex].range()[1]) +")")

                g_mouse.select(".mouse-xaxis-rect_" + scrollIndex + '_' + facetIndex)
                  .attr('x', function(d){
                    if(xaxis.type == 'time'){
                      return -(textWidth(d3.timeFormat((xaxis.format != null)?xaxis.format:'%d %b %Y')(x_val) + ((xaxis.suffix != null)? xaxis.suffix: ''), xaxis.tick.size, xaxis.tick.weight, font.family) + 6)/2
                    }
                    else{
                      return -(textWidth(d3.format((xaxis.format != null)?xaxis.format:'')(x_val) + ((xaxis.suffix != null)? xaxis.suffix: ''), xaxis.tick.size, xaxis.tick.weight, font.family) + 6)/2
                    }
                  })
                  .attr('width', function(d){
                    if(xaxis.type == 'time'){
                      return textWidth(d3.timeFormat((xaxis.format != null)?xaxis.format:'%d %b %Y')(x_val) + ((xaxis.suffix != null)? xaxis.suffix: ''), xaxis.tick.size, xaxis.tick.weight, font.family) + 6
                    }
                    else{
                      return textWidth(d3.format((xaxis.format != null)?xaxis.format:'')(x_val) + ((xaxis.suffix != null)? xaxis.suffix: ''), xaxis.tick.size, xaxis.tick.weight, font.family) + 6
                    }
                  });

                g_mouse.select(".mouse-xaxis-text_" + scrollIndex + '_' + facetIndex)
                  .text(function(d){
                    if(xaxis.type == 'time'){
                      return d3.timeFormat((xaxis.format != null)?xaxis.format:'%d %b %Y')(x_val) + ((xaxis.suffix != null)? xaxis.suffix: '')
                    }
                    else{
                      return d3.format((xaxis.format != null)?xaxis.format:'')(x_val) + ((xaxis.suffix != null)? xaxis.suffix: '')
                    }
                  });

                // <--- X-axis Tooltip ---


                dataPlot[scrollIndex][facetIndex].forEach(function(vGroup, iGroup){
                  if(vGroup[switcherIndex]['data'].filter(d => d['x_orig'] == x_val).length > 0){
                      vGroup[switcherIndex]['data'].filter(d => d['x_orig'] == x_val).forEach(function(vObs, iObs){

                        if(vObs != undefined){

                          var maxTextWidth = 0;
                          var rectHeight = 0;
                          var hoverText = [];

                          tooltip_text.forEach(function(vTooltipLine, iTooltipLine, aTooltipLine){
                            var val = '';
                            rectHeight += (vTooltipLine.size*1.1);

                            vTooltipLine['text'].forEach(function(vTooltipLineText, iTooltipLineText){
                              val = val.concat(
                                ((vTooltipLineText['prefix'] != null)?vTooltipLineText['prefix']:'') + ((vTooltipLineText['var'] != null)?((vTooltipLineText['format'] != null)? d3.format(vTooltipLineText['format'])(vObs[vTooltipLineText['var']]): vObs[vTooltipLineText['var']]): '') + ((vTooltipLineText['suffix'] != null)?vTooltipLineText['suffix']:'')
                              )
                            })
                            maxTextWidth = (textWidth(val, vTooltipLine.size, vTooltipLine.weight) > maxTextWidth)? textWidth(val, vTooltipLine.size, vTooltipLine.weight): maxTextWidth;

                            hoverText.push({
                              'value': val.replace('<br>', ' ').replace('\n', ' '),
                              'size': vTooltipLine.size,
                              'weight': vTooltipLine.weight
                            });
                          });

                          var thisX = (vObs['x'] > ((xScale[scrollIndex][facetIndex].range()[1] - xScale[scrollIndex][facetIndex].range()[0])/2))? (vObs['x'] - (margin.yaxisLabel+margin.yaxis+xaxis.offset.left) - ((maxTextWidth+20)/2) - 7): (vObs['x'] - (margin.yaxisLabel+margin.yaxis+xaxis.offset.left) + ((maxTextWidth+20)/2) + 7);
                          var thisY = vObs['y']  - (yaxis.offset.top) - ((rectHeight+6)/2);

                          var circleX = (vObs['x'] > ((xScale[scrollIndex][facetIndex].range()[1] - xScale[scrollIndex][facetIndex].range()[0])/2))? ( ((maxTextWidth+20)/2) + 7): ( - ((maxTextWidth+20)/2) - 7);
                          var circleY = ((rectHeight+6)/2);



                          g_mouse.select(".mouse-per-line_" + scrollIndex + '_' + facetIndex + '_' + iGroup)
                            //.attr('transform', "translate(" + (vObs['x'] - (margin.yaxisLabel+margin.yaxis+xaxis.offset.left)) + "," + (vObs['y']  - (yaxis.offset.top)) +")")
                            .attr('transform', `translate(${(thisX)}, ${(thisY)})`)

                          if((group.var == null || (group.show != undefined && !group.show)) || svg.select('.legend_' + iGroup).attr('opacity') == 1){
                            g_mouse.select(".mouse-per-line_" + scrollIndex + '_' + facetIndex + '_' + iGroup)
                            //.attr('opacity', "1");
                            .attr('visibility', 'visible');
                          }


                          g_mouse.select(".mouse-rect_" + scrollIndex + '_' + facetIndex + '_' + iGroup)
                            //.attr('width', textWidth(d3.format((yaxis.format != null)?yaxis.format:'')(vObs['y_orig']) + ((yaxis.suffix != null)? yaxis.suffix: ''), yaxis.tick.size, yaxis.tick.weight, font.family) + 6);
                            //.attr('x', 7)
                            //.attr('y', -(rectHeight+6)/2)
                            .attr('width', maxTextWidth + 20)
                            .attr('height', rectHeight + 6)
                            .attr('x', -((maxTextWidth + 20)*0.5));


                          g_mouse.select(".mouse-circ_" + scrollIndex + '_' + facetIndex + '_' + iGroup)
                            .attr('cx', circleX)
                            .attr('cy', circleY);


                          g_mouse.select(".mouse-text_" + scrollIndex + '_' + facetIndex + '_' + iGroup).selectAll('tspan').remove();

                          var dy = 0;
                          hoverText.forEach(function(vHover, iHover){
                            g_mouse.select(".mouse-text_" + scrollIndex + '_' + facetIndex + '_' + iGroup).append('tspan')
                                .style('font-size', vHover['size'])
                                .style('font-weight', vHover['weight'])
                                .attr('x', 0)
                                .attr('y', 0)
                                .attr('dy', dy + 'px')
                                .text(vHover['value']);

                            dy += 1.1*vHover['size'];
                          })


                          //g_mouse.select(".mouse-text_" + scrollIndex + '_' + facetIndex + '_' + iGroup)
                          //  .text(d3.format((yaxis.format != null)?yaxis.format:'')(vObs['y_orig']) + ((yaxis.suffix != null)? yaxis.suffix: ''));
                        }
                      })
                  }
                  else{
                    svg.selectAll(".mouse-per-line_" + scrollIndex + '_' + facetIndex + '_' + iGroup)
                    //.attr('opacity', "0");
                    .attr('visibility', 'hidden');
                  }
                })
          });
          // <--- Add hover area for Tooltip texts ---

        // <-----------------------------
        // <---- Mouse-Over Effects -----
        // <-----------------------------

    });
  });


  // <-----------------
  // <----- CHART -----
  // <-----------------










  // ------------------->
  // ----- TOOLTIP ----->
  // ------------------->

  var tooltip = svg.append('g')
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
    .style('dominant-baseline', "hanging")
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

function chart_bar_horizontal(
  data,
  html_id,

  x={var:null, ascending:true, ci:[null, null]}, // Must be numeric
  y={var:null, order:'as_appear', ascending:true, highlight:{var:null, title:null}}, // Must be categorical

  title={value:[{size:40, weight:700, text:null}, {size:32, weight:700, text:null}], line:false},

  clr={
    var:'clr',
    palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
    value:'#e32726'
  }, // Variable containing color of bar(s), a name of a pre-defined palette of colors, or value to set all bars to same color
  opacity={var:null, value:1.0}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

  facet={var:null, size:18, weight:400, space_above_title:5, order:'as_appear', ascending:true, line:{show:false, color:'#d3d2d2'}},
  group={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, show:true},
  switcher={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},
  scroll={var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},

  bar={
    size:16, weight:400,
    text:null, // Array of arrays: [{var:'n', format:',', prefix:null, suffix:null}, {var:'pct', format:'.1f', prefix:null, suffix:'%'}]
    extra_height:0,
    space_between:5,
    var:null // A variable in the data that takes value between 0 and 1 to indicate height of the bar
  },

  tooltip_text=[
    {size:14, weight:400, text:[{var:'pct', format:'.1f', prefix:null, suffix:'%'}]},
    {size:14, weight:400, text:[
      {var:'n', format:',.0f', prefix:null, suffix:null},
      {var:'tot', format:',.0f', prefix:'/', suffix:null}
    ]}
  ],

  barmode='group', // 'group' or 'stack'

  column_data = {
    before_x:null, //{var:'n', format:',.0f', prefix:null, suffix:null, size:12, weight:400, color:{var:'_clr', value:null}, label:{value:null, size:20, weight:700, padding:{top:0, bottom:0}}}
    after_x:null //{var:'n', format:',.0f', prefix:null, suffix:null, size:12, weight:400, color:{var:'_clr', value:null}, label:{value:null, size:20, weight:700, padding:{top:0, bottom:0}}}
  },

  vline={
    var:{name:'bench', line_style:'dashed', clr:'black', width:2, label:null},
    value:[
      {x:50, line_style:'dashed', clr:'black', width:2, label:null}
    ]
  },

  xaxis={
    range: [null, null],
    rangeScroll:'fixed', // 'fixed' or 'free'
    rangeFacet:'fixed', // 'fixed' or 'free'
    format:null,
    suffix: null,
    tick:{size:14, weight:400, orientation:'h', splitWidth:150},
    label:{value:null, size:20, weight:700},
    offset:{left:10, right:10},
    show:true,
    show_line:true,
    show_ticks:true,
    num_ticks:null,
    show_grid:false
  },

  yaxis={
    widthPct:{value:0.4, range:'free', cutText:false}, // Max. percentage of the chart width that the y-axis can occupy [value: between 0 and 1; range: 'fixed' or 'free']
    rangeScroll:'fixed', // 'fixed' or 'free'
    rangeFacet:'fixed', // 'fixed' or 'free'
    tick:{size:16, weight:400},
    label:{value:null, size:20, weight:700},
    offset:{top:10, bottom:10},
    show:true,
    show_line:true,
    show_ticks:true,
  },

  font={family:'Catamaran'},

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
        .attr('x', -99999)
        .attr('y', -99999)
        .style('font-family', fontFamily)
        .style('font-size', fontSize + 'px')
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
          yThis = text.attr('y'),
          xThis = text.attr('x'),
          dy = parseFloat(text.attr('dy')),
          textSplit = splitWrapText(text.text(), width=width, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily),
          tspan = text.text(null);

      var vshift = (valign == 'bottom')? 0: (valign == 'top')? (1.1): (1.1/2)

      textSplit.forEach(function(v, i, a){

          text.append('tspan')
              .attr('x', xThis)
              .attr('y', yThis)
              .attr('dy', `${((i * lineHeight) - ((a.length-1)*vshift) + (dy_extra))}em`)
              .text(v)
      });
    })

  }

  // <--------------------------------------------------------
  // <----- Function to add TSPAN for each split-up text -----
  // <--------------------------------------------------------





  // --------------------------------------------------------------->
  // ----- Function to shorten text to fit into assigned width ----->
  // --------------------------------------------------------------->

  function shortenText(text, width=100, additionalText="", fontSize=14, fontWeight=400, fontFamily=font.family) {

      var textShortened = [];

      var textSplit = text.split(/\n|<br>/);

      if(textWidth(textSplit[0] + additionalText, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) > width){
        //console.log('# WIDTH', textWidth(textSplit[0] + additionalText, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily), '#', textSplit[0])
        var numWords = textSplit[0].trim().split(/\s+/).length;

        while (numWords > 0) {
          var lastWordIndex = textSplit[0].lastIndexOf(" ");
          textSplit[0] = textSplit[0].substring(0, lastWordIndex);
          numWords = textSplit[0].trim().split(/\s+/).length;

          //console.log('# WIDTH', textWidth(textSplit[0] + additionalText, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily), '#', textSplit[0])

          if(textWidth(textSplit[0] + additionalText, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) <= width){
            return textSplit[0] + additionalText
          }

          if(numWords == 1){
            var numLetters = textSplit[0].length;
            while (numLetters > 0) {
              textSplit[0] = textSplit[0].slice(0, -1);

              if(textWidth(textSplit[0] + additionalText, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) <= width){
                return textSplit[0] + additionalText
              }

              numLetters = textSplit[0].length;
            }
          }

        }
      }
      else{
        if(textSplit.length > 1){
          return textSplit[0] + additionalText
        }
        else{
          return textSplit[0]
        }
      }

  }

  // <---------------------------------------------------------------
  // <----- Function to shorten text to fit into assigned width -----
  // <---------------------------------------------------------------





  // ---------------------------------------------------->
  // ----- Function to add TSPAN for shortened text ----->
  // ---------------------------------------------------->

  function shortenTextSpan(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family, valign='bottom', dy_extra=0) {

    text.each(function() {

      var text = d3.select(this),
          lineNumber = 0,
          lineHeight = 1.1, // ems
          yThis = text.attr('y'),
          xThis = text.attr('x'),
          dy = parseFloat(text.attr('dy')),
          textSplit = [shortenText(text.text(), width=width, additionalText="...", fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily)],
          tspan = text.text(null);


      var vshift = (valign == 'bottom')? 0: (valign == 'top')? (1.1): (1.1/2)

      textSplit.forEach(function(v, i, a){
          text.append('tspan')
              .attr('x', xThis)
              .attr('y', yThis)
              .attr('dy', `${((i * lineHeight) - ((a.length-1)*vshift) + (dy_extra))}em`)
              .text(v)
      });
    })

  }

  // <---------------------------------------------------------
  // <----- Function to add TSPAN for each shortened text -----
  // <---------------------------------------------------------





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
            //'max-width-value': maxTextWidth
          })
        });

        listSplitWrappedText.forEach(function(vListSplitWrappedText, iListSplitWrappedText){
          vListSplitWrappedText['max-width-value'] = maxTextWidth;
        });

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





  // ---------------------------------------->
  // ----- Function to add text to bars ----->
  // ---------------------------------------->

  function barText(d, iScroll, iFacet){

    d.each(function(v, i){

        var text = d3.select(this)
        var lineHeight = 1.1; // ems
        var yThis = text.attr('y');
        var xThis = text.attr('x');
        var groupThis = text['_groups'][0][0].getAttribute('class').split(' ')[1]


        bar.text.forEach(function(v2, i2, a2){

          var text_val = ((v2['prefix'] != null && v[v2['var']] != null)?v2['prefix']:'') + ((v2['var'] != null)?((v[v2['var']] != null)?d3.format(v2['format'])(v[v2['var']]): ''): '') + ((v2['suffix'] != null && v[v2['var']] != null)?v2['suffix']:'');

          text.append('tspan')
              .attr('opacity', 1.0)
              .attr('visibility', 'visible')
              .attr('class', function(d){ return 'tspan_' + i2 + ' ' + groupThis })
              .attr('x', xThis)
              .attr('y', yThis)
              .attr('text-value', v[v2['var']])
              .attr('rect-width', function(d){
                return xScale[iScroll][iFacet](v['endRect']) - xScale[iScroll][iFacet](v['startRect'])
              })
              .attr('dy', `${(i2 * lineHeight) - ((1.1/2)*(bar.text.length))}em`)
              .style('font-size', d => (((rectHeightScale(d['heightPctRect'])-6)/1.1) >= bar.size)? bar.size + 'px': ((rectHeightScale(d['heightPctRect'])-6)/1.1) + 'px')
              .text(function(){
                if(v['text_location'] == 'inside'){
                  if(textWidth(text_val, fontSize=bar.size, fontWeight=bar.weight, fontFamily=font.family) < ((xScale[iScroll][iFacet](v['endRect']) - xScale[iScroll][iFacet](v['startRect']))-6)){
                    return text_val
                  }
                  else{ return ''}
                }
                else{
                  return text_val
                }
              });

        });

    });

  }

  // <----------------------------------------
  // <----- Function to add text to bars -----
  // <----------------------------------------





  // ----------------------------------------------->
  // ----- Function to transition text in bars ----->
  // ----------------------------------------------->

  function barTransition(d, iScroll, iFacet){

    d.each(function(v, i){

        var text = d3.select(this)
        //var lineHeight = 1.1; // ems
        //var y = text.attr('y');
        //var x = text.attr('x');

        bar.text.forEach(function(v2, i2, a2){

          text.select(".tspan_" + i2)
              .transition()
              .duration(800)
              .attr('text-value', v[v2['var']])
              .attr('rect-width', function(d){
                return xScale[iScroll][iFacet](v['endRect']) - xScale[iScroll][iFacet](v['startRect'])
              })
              .attr('x', function(d){
                if(v['text_location'] == 'inside'){
                  return Math.min(xScale[iScroll][iFacet](v['startRect']), xScale[iScroll][iFacet](v['endRect'])) + ((Math.abs(xScale[iScroll][iFacet](v['startRect']) - xScale[iScroll][iFacet](v['endRect'])))/2)
                }
                else{
                  if(x.ci[0] != null && x.ci[1] != null){
                    return xScale[iScroll][iFacet](v['x_ci_u'])
                  }
                  else{
                    return xScale[iScroll][iFacet](v['endRect'])
                  }
                }
              })
              //.style('font-size', d => (((rectHeightScale(d['heightPctRect'])/1.1)-6 >= bar.size)? bar.size: (rectHeightScale(d['heightPctRect'])/1.1)-6) + 'px')
              .style('font-size', d => (((rectHeightScale(d['heightPctRect'])-6)/1.1) >= bar.size)? bar.size+'px': ((rectHeightScale(d['heightPctRect'])-6)/1.1) + 'px')
              .textTween(function(d) {
                const element = this;
                const initialTextValue = parseFloat(element.getAttribute('text-value'));
                const initialRectWidth = parseFloat(element.getAttribute('rect-width'));
                const i = d3.interpolate(initialTextValue, v[v2['var']]);
                const j = d3.interpolate(initialRectWidth, Math.abs(xScale[iScroll][iFacet](v['endRect']) - xScale[iScroll][iFacet](v['startRect'])));

                //const i = d3.interpolate($(this).attr('text-value'), v[v2['var']]);
                //const j = d3.interpolate($(this).attr('rect-width'), Math.abs(xScale[iScroll][iFacet](v['endRect']) - xScale[iScroll][iFacet](v['startRect'])));
                return function(t) {

                  if(v['text_location'] == 'inside'){
                      if(isNaN(parseFloat(i(t)))){
                        return ' ';
                      }
                      else if( textWidth(
                          text=((v2['prefix'] != null && i(t) != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null && i(t) != null)?v2['suffix']:''),
                          fontSize=(((rectHeightScale(d['heightPctRect'])-6)/1.1) >= bar.size)? bar.size: ((rectHeightScale(d['heightPctRect'])-6)/1.1), //bar.size,
                          fontWeight=bar.weight,
                          fontFamily=font.family
                      ) < (j(t)-6) ){
                        return ((v2['prefix'] != null && i(t) != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null && i(t) != null)?v2['suffix']:'');
                      }
                      else {
                        return ' ';
                      }
                  }
                  else{
                    if(isNaN(parseFloat(i(t)))){
                      return ' ';
                    }
                    else{
                      return ((v2['prefix'] != null && i(t) != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null && i(t) != null)?v2['suffix']:'');
                    }
                  }

                };
              })

        });

    });

  }

  // <-----------------------------------------------
  // <----- Function to transition text in bars -----
  // <-----------------------------------------------





  // -------------------------------------------------->
  // ----- Function to transition text in columns ----->
  // -------------------------------------------------->

  function columnBeforeTransition(d){

    d.each(function(v, i){

      var text = d3.select(this);

      text.transition()
          .duration(800)
          .attr('text-num', function(d){
            if(d[column_data.before_x['var']]){
              return d[column_data.before_x['var']]
            }
            else{
              return 0;
            }
          })
          .attr('text-char', function(d){
            if(d[column_data.before_x['var']]){
              return d[column_data.before_x['var']]
            }
            else{
              return '';
            }
          })
          .textTween(function(d) {
            var element = this;
            var from_i = (element.getAttribute('text-num') != null) ? parseFloat(element.getAttribute('text-num')) : 0;
            var to_i = (v[column_data.before_x['var']])? ( (v[column_data.before_x['var']] != null)? v[column_data.before_x['var']]: 0 ) :  0;
            var from_char = element.getAttribute('text-char');

            //var from_i = ($(this).attr('text-num') != null)? $(this).attr('text-num'): 0;
            //var to_i = (v[column_data.before_x['var']])? ( (v[column_data.before_x['var']] != null)? v[column_data.before_x['var']]: 0 ) :  0;
            //var from_char = $(this).attr('text-char');

            const i = d3.interpolate(from_i, to_i);
            return function(t) {

                if(from_char == '' && !d[column_data.before_x['var']]){
                  return ''
                }
                else if(t == 1 && !d[column_data.before_x['var']]){
                  return ''
                }
                else{
                  return ((column_data.before_x['prefix'] != null)?column_data.before_x['prefix']:'') + ((column_data.before_x['var'] != null)?(d3.format(column_data.before_x['format'])(parseFloat(i(t)))): '') + ((column_data.before_x['suffix'] != null)?column_data.before_x['suffix']:'');
                }

            };
          })
    });
  }



  function columnAfterTransition(d){

    d.each(function(v, i){

      var text = d3.select(this);

      text.transition()
          .duration(800)
          .attr('text-num', function(d){
            if(d[column_data.after_x['var']]){
              return d[column_data.after_x['var']]
            }
            else{
              return 0;
            }
          })
          .attr('text-char', function(d){
            if(d[column_data.after_x['var']]){
              return d[column_data.after_x['var']]
            }
            else{
              return '';
            }
          })
          .textTween(function(d) {
            var element = this;
            var from_i = (element.getAttribute('text-num') != null) ? parseFloat(element.getAttribute('text-num')) : 0;
            var to_i = (v[column_data.after_x['var']])? ( (v[column_data.after_x['var']] != null)? v[column_data.after_x['var']]: 0 ) :  0;
            var from_char = element.getAttribute('text-char');


            //var from_i = ($(this).attr('text-num') != null)? $(this).attr('text-num'): 0;
            //var to_i = (v[column_data.after_x['var']])? ( (v[column_data.after_x['var']] != null)? v[column_data.after_x['var']]: 0 ) :  0;
            //var from_char = $(this).attr('text-char');

            const i = d3.interpolate(from_i, to_i);
            return function(t) {

                if(from_char == '' && !d[column_data.after_x['var']]){
                  return ''
                }
                else if(t == 1 && !d[column_data.after_x['var']]){
                  return ''
                }
                else{
                  return ((column_data.after_x['prefix'] != null)?column_data.after_x['prefix']:'') + ((column_data.after_x['var'] != null)?(d3.format(column_data.after_x['format'])(parseFloat(i(t)))): '') + ((column_data.after_x['suffix'] != null)?column_data.after_x['suffix']:'');
                }

            };
          })
    });
  }

  // <--------------------------------------------------
  // <----- Function to transition text in columns -----
  // <--------------------------------------------------





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
    svg.select('.g_scroll_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('x', function(){
            (method == 'up')? canvas.width: -canvas.width
          })
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${((canvas.width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label})`
            }
            else{
              return `translate(${((-canvas.width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('x', canvas.width*0)
          .attr('transform', function(){
              return `translate(${(margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label})`
          })


    svg.select('.g_scroll_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('x', function(){
            (method == 'up')? -canvas.width: canvas.width
          })
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas.width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label})`
            }
            else{
              return `translate(${(canvas.width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label})`
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





  // -------------------------------------------------------->
  // ----- Function to decide if color is light or dark ----->
  // -------------------------------------------------------->

  function lightOrDark(color) {

    // Variables for red, green, blue values
    var r, g, b, hsp;

    // Check the format of the color, HEX or RGB?
    if (color.match(/^rgb/)) {

        // If RGB --> store the red, green, blue values in separate variables
        color = color.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$/);

        r = color[1];
        g = color[2];
        b = color[3];
    }
    else {

        // If hex --> Convert it to RGB: http://gist.github.com/983661
        color = +("0x" + color.slice(1).replace(
        color.length < 5 && /./g, '$&$&'));

        r = color >> 16;
        g = color >> 8 & 255;
        b = color & 255;
    }

    // HSP (Highly Sensitive Poo) equation from http://alienryderflex.com/hsp.html
    hsp = Math.sqrt(
    0.299 * (r * r) +
    0.587 * (g * g) +
    0.114 * (b * b)
    );

    // Using the HSP value, determine whether the color is light or dark
    // if (hsp>127.5) {
    if (hsp>128.5) {

        return 'light';
    }
    else {

        return 'dark';
    }
  }

  // <--------------------------------------------------------
  // <----- Function to decide if color is light or dark -----
  // <--------------------------------------------------------





  // ------------------------------------------->
  // ---- Function to change Bars and Text ----->
  // ------------------------------------------->

  function changeBars(iSwitch){

    dataPlot.forEach(function(vScroll, iScroll){
      vScroll.forEach(function(vFacet, iFacet){

            svg.selectAll('.scroll_' + iScroll)
              .filter('.facet_' + iFacet)
              .data(vFacet[iSwitch])
                .transition()
                .attr('class', function(d, i){
                  return 'scroll_' + iScroll +
                  ' switcher_' + iSwitch +
                  ' facet_' + iFacet +
                  ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                  ' obs_' + iScroll + '_' + iSwitch + '_' + iFacet + '_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i +
                  ' yval yval_' + domainY.indexOf(d['y'])
                })
                .attr('startRect', d => xScale[iScroll][iFacet](d['startRect']))
                .attr('endRect', d => xScale[iScroll][iFacet](d['endRect']))
                .attr('widthRect', d => xScale[iScroll][iFacet](d['endRect']) - xScale[iScroll][iFacet](d['startRect']))
                .attr('color-value', d => d['_clr'])
                .attr('group-value', function(d){
                  if(group.var != null){ return d['group'] }
                  else{ return '' }
                })
                .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                .attr('x-value', d => d[x.var])
                .attr('y-value', function(d){
                  //if(barmode == 'group'){ return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) }
                  if(barmode == 'group'){ return yScale[iScroll][iFacet](d['y']) + (height.bar*(domainGroup.map(d => d['group']).indexOf(d['group']))) }
                  else{ return yScale[iScroll][iFacet](d['y']) }
                });


            svg.select('.g_scroll_' + iScroll)
              .select('.facet_' + iFacet)
              .selectAll('.bar_rect')
              .data(vFacet[iSwitch])
              .transition()
                .duration(800)
                .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                .attr('x', function(d){ return xScale[iScroll][iFacet](d['startRect']) })
                .attr('y', function(d, i){
                  if(barmode == 'group'){
                    return (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (rectHeightScale(d['heightPctRect'])/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) //(height.bar/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                  }
                  else{
                    return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (rectHeightScale(d['heightPctRect'])/2) //(height.bar/2)
                  }
                })
                .attr('width', function(d){ return Math.abs(xScale[iScroll][iFacet](d['endRect']) - xScale[iScroll][iFacet](d['startRect'])) })
                .attr('height', function(d){
                  return rectHeightScale(d['heightPctRect']) //height.bar*d['heightPctRect'] //height.bar*rectHeightScale(d['heightPctRect'])
                });



            svg.select('.g_scroll_' + iScroll)
              .select('.facet_' + iFacet)
              .selectAll('.bar_text')
              .data(vFacet[iSwitch])
              .each(d => d)
              .call(barTransition, iScroll, iFacet);



            if(column_data.before_x != null){
                svg.select('.g_scroll_' + iScroll).select('.facet_' + iFacet).selectAll('.column_data_before_x')
                  .data(vFacet[iSwitch])
                  .each(d => d)
                  .call(columnBeforeTransition);
            }


            if(column_data.after_x != null){
                svg.select('.g_scroll_' + iScroll).select('.facet_' + iFacet).selectAll('.column_data_after_x')
                  .data(vFacet[iSwitch])
                  .each(d => d)
                  .call(columnAfterTransition);
            }


            if(x.ci[0] != null && x.ci[1] != null){
              svg.select('.g_scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .selectAll('.bar_ci')
                .data(vFacet[iSwitch])
                .transition()
                  .duration(800)
                    .attr('x-value', d => d['x'])
                    .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                    .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                    .attr('d', d =>
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3)  +
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) +
                    'M' + xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3) +
                    'M' + xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 5) + 'L' +  xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 5)
                    )
            }


        //  })
        })
      });

  };

  // <-------------------------------------------
  // <---- Function to change Bars and Text -----
  // <-------------------------------------------










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>


  // --- Scroll domain --->
  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  //console.log('### domainScroll', domainScroll);





  // --- Y-axis domain --->
  var domainY = Array.from(new Set(data.map(d => d[y.var].toString())));
  if(y.order == 'alphabetical'){ domainY.sort(); }
  //console.log('domainY', domainY);





  // --- Facet domain --->
  var domainFacet = []
  domainScroll.forEach(function(vScroll, iScroll){
    domainFacet[iScroll] = []

    if(facet.var != null){
      Array.from(new Set(data.filter(d => (scroll.var != null)? (d[scroll.var] == vScroll): true).map(d => d[facet.var].toString()))).forEach(function(vFacet, iFacet){

          if(yaxis.rangeFacet == 'free'){
            if(yaxis.rangeScroll == 'free'){
              var facetY = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[y.var].toString())));
            }
            else{
              var facetY = Array.from(new Set(data.filter(d => d[facet.var] == vFacet).map(d => d[y.var].toString())));
            }
          }
          else{
            if(yaxis.rangeScroll == 'free'){
              var facetY = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[y.var].toString())));
            }
            else{
              var facetY = Array.from(new Set(data.map(d => d[y.var].toString())));
            }
          }

          if(y.order == 'alphabetical'){ facetY.sort(); }
          if(!y.ascending){ facetY.reverse(); }

        domainFacet[iScroll][iFacet] = {'facet': vFacet, 'y': facetY}
      })
    }
    else{

      if(yaxis.rangeScroll == 'free'){
        var facetY = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[y.var].toString())));
      }
      else{
        var facetY = Array.from(new Set(data.map(d => d[y.var].toString())));
      }

      if(y.order == 'alphabetical'){ facetY.sort(); }
      if(!y.ascending){ facetY.reverse(); }

      domainFacet[iScroll][0] = {'facet': null, 'y': facetY}

    }


    if(facet.order == 'alphabetical'){ domainFacet[iScroll].sort((a, b) => d3.ascending(a['facet'], b['facet'])); }
    if(!facet.ascending){ domainFacet[iScroll].reverse(); }

  })
  //console.log('domainFacet', domainFacet);





  // --- Group domain --->
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




  // --- Switcher domain --->
  var domainSwitcher = (switcher.var != null)? Array.from(new Set(data.map(d => d[switcher.var]))): [null];
  if(switcher.var != null && switcher.order == 'alphabetical'){ domainSwitcher.sort(); }
  //console.log('### domainSwitcher', domainSwitcher);

  // <------------------------
  // <----- DATA DOMAINS -----
  // <------------------------








  if (bar.var == undefined){
    bar.var = null
  }

  var height = {
    'bar': (bar.text != null)? ( (((bar.size*1.1)*bar.text.length)+6) + bar.extra_height ) : ( ((bar.size*1.1)+6) + bar.extra_height )
  };

  var rectHeightScale = d3.scaleLinear()
  .domain([0, 1])
  .range([
    Math.min(12.6, height.bar),
    Math.max(12.6, height.bar)
  ]);


  // ---------------->
  // ----- DATA ----->
  // ---------------->
  var dataPlot = [];

  domainScroll.forEach(function(vScroll, iScroll){
    dataPlot[iScroll] = []

    domainFacet[iScroll].forEach(function(vFacet, iFacet){
      dataPlot[iScroll][iFacet] = [];

      var minXvalue = (xaxis.range[0] != null)? xaxis.range[0]: d3.min(data, d => d[x.var]);
      if(xaxis.rangeScroll == 'fixed' && xaxis.rangeFacet == 'fixed'){
        var minXvalue = (xaxis.range[0] != null)? xaxis.range[0]: d3.min(data, d => d[x.var]);
      }
      else if(xaxis.rangeScroll == 'fixed' && xaxis.rangeFacet == 'free'){
        var minXvalue = (xaxis.range[0] != null)? xaxis.range[0]: d3.min(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true)), d => d[x.var]);
      }
      else if(xaxis.rangeScroll == 'free' && xaxis.rangeFacet == 'fixed'){
        var minXvalue = (xaxis.range[0] != null)? xaxis.range[0]: d3.min(data.filter(d => ((facet.var != null)? d[facet.var] == vFacet['facet']: true)), d => d[x.var]);
      }
      else{
        var minXvalue = (xaxis.range[0] != null)? xaxis.range[0]: d3.min(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true)), d => d[x.var]);
      }

      domainSwitcher.forEach(function(vSwitcher, iSwitcher){
        dataPlot[iScroll][iFacet][iSwitcher] = [];

        vFacet['y'].forEach(function(vY, iY){

          var startRect = minXvalue;

          domainGroup.forEach(function(vGroup, iGroup){

              data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) && d[y.var] == vY).forEach(function(vDataObs, iDataObs, aDataObs){

                  // Color of bar
                  var newObs_clr;
                  if(group.var != null){
                    newObs_clr = domainGroup.map(d => d['color'])[iGroup];
                  }
                  else{
                    if(clr.var != null){
                      newObs_clr = vDataObs[clr.var];
                    }
                    else if(clr.palette != null){
                      newObs_clr = domainGroup.map(d => d['color'])[iGroup];
                    }
                    else{
                      newObs_clr = (clr.value != null)? clr.value: '#e32726';
                    }
                  }

                  var newObs = {
                    'switcher': vSwitcher,
                    'facet': (facet.var != null)? vDataObs[facet.var]: null,
                    'group': (group.var != null)? vGroup['group']: null,
                    'group_index': (group.var != null)? domainGroup.map(d => d['group']).indexOf(vGroup['group']): null,
                    '_clr': newObs_clr,
                    //'_stroke_clr': (barmode == 'stack' || aDataObs.length > 1)? ((newObs_clr == 'white' ||newObs_clr == 'rgb(255,255,255)' || newObs_clr == '#fff' || newObs_clr == '#ffffff')?'#d3d2d2': 'white'): newObs_clr,
                    '_stroke_clr': ((newObs_clr == 'white' ||newObs_clr == 'rgb(255,255,255)' || newObs_clr == '#fff' || newObs_clr == '#ffffff')?'#d3d2d2': 'white'),
                    'opacity': (opacity.var != null)? vDataObs[opacity.var] : ((opacity.value != null)? opacity.value: 1.0),
                    'y': vY,
                    'x': vDataObs[x.var],
                    'x_ci_l': (x.ci[0] != null)? vDataObs[x.ci[0]]: vDataObs[x.var],
                    'x_ci_u': (x.ci[1] != null)? vDataObs[x.ci[1]]: vDataObs[x.var],
                    'startRect': startRect,
                    'endRect': (minXvalue < 0)? (startRect + (vDataObs[x.var] - minXvalue)): (startRect + vDataObs[x.var]),
                    'heightPctRect': (bar.var != null)? ((vDataObs[bar.var] != null)? vDataObs[bar.var]: 1): 1,
                    'text_location': (barmode == 'stack' || aDataObs.length > 1)? 'inside': 'outside'
                  }


                  if(barmode == 'stack' || (barmode != 'group' && aDataObs.length > 1)){
                    startRect += vDataObs[x.var]
                  }
                  else{
                    startRect = minXvalue;
                  }

                  if(bar.text != null){
                    bar.text.forEach((v, i) => {
                        newObs[v['var']] = vDataObs[v['var']]
                    });
                  }

                  if(tooltip_text != null){
                    tooltip_text.forEach((v, i) => {
                        v['text'].forEach((v2, i2) => {
                          newObs[v2['var']] = vDataObs[v2['var']]
                        })
                    });
                  }

                  if(column_data.before_x != null){
                    newObs[column_data.before_x['var']] = vDataObs[column_data.before_x['var']]
                    if(column_data.before_x['color'].var != null){
                      newObs[column_data.before_x['color'].var] = vDataObs[column_data.before_x['color'].var]
                    }
                  }

                  if(column_data.after_x != null){
                    newObs[column_data.after_x['var']] = vDataObs[column_data.after_x['var']]
                    if(column_data.after_x['color'].var != null){
                      newObs[column_data.after_x['color'].var] = vDataObs[column_data.after_x['color'].var]
                    }
                  }

                  if(vline.var != null){
                    newObs[vline.var['name']] = vDataObs[vline.var['name']]
                  }

                  dataPlot[iScroll][iFacet][iSwitcher].push(newObs);
              })

          })
        })
      })
    })
  })
  //console.log('### dataPlot', dataPlot);

  // <----------------
  // <----- DATA -----
  // <----------------










  // ------------------------>
  // ----- Graph Sizing ----->
  // ------------------------>

  //var canvas.width = 960;
  if (canvas == undefined){
    var canvas = {width:960}
  }
  if(canvas.width == null){
    canvas.width = 960
  }

  if (y.highlight == undefined){
    y.highlight = {var:null, title:null}
  }
  else if(y.highlight.title == undefined){
    y.highlight.title = null;
  }

  if (yaxis.widthPct == undefined){
    yaxis.widthPct = {value:0.4, range:'free', cutText:false}
  }




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
  //console.log('title_ypos', title_ypos)
  //console.log('height.title', height.title)



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
      //height.switcher += height.switcherLabel
    }

    height.switcher = margin.g + maxY + (maxRowInLastLine*(switcher.size*1.1)) + 10 + height.switcherLabel
  }



  // Legend Height
  height.legend = 0;
  height.legendLabel = 0;

  var legendValues = [];

  // Group legend items
  if(group.var != null ){
    if(group.show == undefined || group.show){
      domainGroup.map(d => d['group']).forEach(function(v,i){
        legendValues.push({
          'text': v,
          'type': 'rect'
        })
      })
    }
  }

  // Vertical lines from Variable legend items
  if(vline.var != null && vline.var.label != null){
    legendValues.push({
      'text': vline.var.label,
      'type': 'line',
      '_clr': vline.var.clr,
      'line_style': vline.var.line_style,
      'width': vline.var.width
    })
  }

  // Vertical lines from values legend items
  if(vline.value != null && vline.value.filter(d => d['label'] != null).map(d => d['label']).length > 0){
    vline.value.filter(d => d['label'] != null).forEach(function(v, i){
      legendValues.push({
        'text': v.label,
        'type': 'line',
        '_clr': v.clr,
        'line_style': v.line_style,
        'width': v.width
      })
    })
  }
  //console.log('legendValues:', legendValues)

  if(legendValues.length > 0){

    var legendText = splitWrapTextElement(legendValues.map(d => d['text']), width=canvas.width-(margin.left+margin.right), padding=10, extra_width=14+5, fSize=group.size, fWeight=group.weight, fFamily=font.family);
    //console.log('legendText:', legendText)

    // Get colors (and line properties, if needed)
    legendText.forEach(function(v, i){
      if(group.var != null && (group.show == undefined || group.show) && i < domainGroup.length){
        v['type'] = 'rect';
        v['color'] = domainGroup[i]['color']
      }
      else{
        v['type'] = legendValues[i]['type'];
        v['color'] = legendValues[i]['_clr'];
        v['line_style'] = legendValues[i]['line_style'];
        v['width'] = legendValues[i]['width'];
      }
    });

    if(group.label.value != null){
      var numLegendLabelLines = splitWrapText(group.label.value, (canvas.width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family).length;
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
  else{
    var legendText = [];
  }
  //console.log('legendText:', legendText)




  height.yaxis0 = []
  domainFacet.forEach(function(vScroll, iScroll){

    var numYValuesInScroll = 0;
    vScroll.forEach(function(vFacet, iFacet){
      numYValuesInScroll += vFacet['y'].length
    })

    //height.yaxis0[iScroll] = (barmode=='group')?  ((((height.bar*domainGroup.length)*100)/90)*numYValuesInScroll): (((height.bar*100)/90)*numYValuesInScroll);
    height.yaxis0[iScroll] = (barmode=='group')?  ((height.bar*domainGroup.length)*numYValuesInScroll) + (((bar.space_between)?bar.space_between:5)*(numYValuesInScroll-1)): (height.bar*numYValuesInScroll) + (((bar.space_between)?bar.space_between:5)*(numYValuesInScroll-1));
  })
  //console.log('height.yaxis0', height.yaxis0)



  margin.yaxisLabel = []
  domainFacet.forEach(function(vScroll, iScroll){
    margin.yaxisLabel[iScroll] = (yaxis.label.value != null)? (yaxis.label.size*1.1)*splitWrapText(yaxis.label.value, height.yaxis0[iScroll], fontSize=yaxis.label.size, fontWeight=yaxis.label.weight, fontFamily=font.family).length + (10) : 0;
  })
  //console.log('height.bar', height.bar)
  //console.log('height.yaxis0', height.yaxis0)
  //console.log('margin.yaxisLabel', margin.yaxisLabel)





  // Calculate margin of y-axis for each scroll
  margin.yaxis = [];
  maxNumTickLines = [];
  domainFacet.forEach(function(vScroll, iScroll){
    maxNumTickLines[iScroll] = 0;
    margin.yaxis[iScroll] = 0;

    if(yaxis.show){

      vScroll.forEach(function(vFacet, iFacet){

          vFacet['y'].forEach(function(vY, iY){
            if(yaxis.widthPct.cutText != undefined && yaxis.widthPct.cutText){

              maxNumTickLines[iScroll] = Math.max(maxNumTickLines[iScroll], 1);
              if(yaxis.widthPct.range == 'fixed'){
                margin.yaxis[iScroll] = ((canvas.width-(margin.left+margin.right))*yaxis.widthPct.value) - margin.yaxisLabel[iScroll];
              }
              else{
                margin.yaxis[iScroll] = Math.max(margin.yaxis[iScroll], textWidth(shortenText(vY, width=((canvas.width-(margin.left+margin.right))*yaxis.widthPct.value) - margin.yaxisLabel[iScroll], additionalText="...", fontSize=yaxis.tick.size, fontWeight=yaxis.tick.weight, fontFamily=font.family), yaxis.tick.size, yaxis.tick.weight, font.family)+20)
              }

            }
            else{

                splitWrapText(vY, (((canvas.width-(margin.left+margin.right))*yaxis.widthPct.value) - margin.yaxisLabel[iScroll]), yaxis.tick.size, yaxis.tick.weight, font.family).forEach(function(vSplit, iSplit, aSplit){

                    maxNumTickLines[iScroll] = Math.max(maxNumTickLines[iScroll], aSplit.length);
                    if(yaxis.widthPct.range == 'fixed'){
                      margin.yaxis[iScroll] = ((canvas.width-(margin.left+margin.right))*yaxis.widthPct.value) - margin.yaxisLabel[iScroll]; //canvas.width*yaxis.widthPct.value
                    }
                    else{
                      margin.yaxis[iScroll] = Math.max(margin.yaxis[iScroll], textWidth(vSplit, yaxis.tick.size, yaxis.tick.weight, font.family)+20)
                    }
                });

            }
          })

      })

    }
  })
  //console.log('margin.yaxis:', margin.yaxis)





  // Re-calculate y-axis height
  height.yaxis = [];
  height.xaxis = [];
  height.xaxisLabel = [];
  domainFacet.forEach(function(vScroll, iScroll){

    var numYvalues = 0;
    var numFacets = 0;
    vScroll.forEach(function(vFacet, iFacet){
      numYvalues += vFacet['y'].length
      numFacets += 1
    })

    if(barmode=='group'){
      if((height.bar*domainGroup.length) < (maxNumTickLines[iScroll]*(yaxis.tick.size*1.1)+6)){
        height.yaxis[iScroll] = ((maxNumTickLines[iScroll]*(yaxis.tick.size*1.1)+6))*numYvalues + (((bar.space_between)?bar.space_between:5)*(numYvalues-1));
      }
      else{
        height.yaxis[iScroll] = (((height.bar*domainGroup.length))*numYvalues) + (((bar.space_between)?bar.space_between:5)*(numYvalues-1));
      }
    }
    else{
      if((maxNumTickLines[iScroll]*(yaxis.tick.size*1.1)) > (((height.bar)*100)/90)){
        height.yaxis[iScroll] = (((maxNumTickLines[iScroll]*(yaxis.tick.size*1.1))+6)*numYvalues) + (((bar.space_between)?bar.space_between:5)*(numYvalues-1));
      }
      else{
        height.yaxis[iScroll] = (height.bar*numYvalues) + (((bar.space_between)?bar.space_between:5)*(numYvalues-1));
      }
    }

    height.yaxis[iScroll] += (yaxis.offset.top + yaxis.offset.bottom)*numFacets;


    if(facet.var != null && xaxis.rangeScroll == 'free'){
      height.xaxis[iScroll] = ( ((xaxis.show)?(xaxis.tick.size*1.1) + 20: 0)*numFacets)
    }
    else{
      height.xaxis[iScroll] = ((xaxis.show)?(xaxis.tick.size*1.1) + 20: 0)
    }



    height.xaxisLabel[iScroll] = (xaxis.label.value != null)? ((xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, (canvas.width - (margin.left + margin.yaxisLabel[iScroll] + margin.yaxis[iScroll] + margin.right)), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length) : 0


  })
  //console.log('height.yaxis', height.yaxis)
  //console.log('height.xaxis', height.xaxis)
  //console.log('height.xaxisLabel', height.xaxisLabel)





  // Facet Height
  var facet_ypos = [];
  height.facetLabel = [];
  height.facet = [];

  domainFacet.forEach(function(vScroll, iScroll){

    var numYvalues = 0, numFacets = 0;
    vScroll.forEach(function(vFacet, iFacet){
      numYvalues += vFacet['y'].length;
      numFacets += 1;
    })

    facet_ypos[iScroll] = [];
    height.facetLabel[iScroll] = [];
    height.facet[iScroll] = 0;

    var facetPos = 0;

    vScroll.forEach(function(vFacet, iFacet){
      var numFacetLabelLines = (vFacet['facet'] != null)? splitWrapText(vFacet['facet'], (canvas.width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length: 0;
      height.facetLabel[iScroll][iFacet] = (numFacetLabelLines*(facet.size*1.1)) + ((facet.var != null)? facet.space_above_title: 0);

      facet_ypos[iScroll][iFacet] = facetPos + height.facetLabel[iScroll][iFacet];

      //facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + ((height.yaxis[iScroll])*(vFacet['y'].length/numYvalues)) + yaxis.offset.bottom + ((xaxis.rangeScroll == 'free')? (height.xaxis[iScroll]/numFacets): 0);
      facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + ((height.yaxis[iScroll])*(vFacet['y'].length/numYvalues)) + yaxis.offset.bottom;
      if(xaxis.rangeScroll == 'free' || (xaxis.rangeScroll == 'fixed' && (iFacet+1) == domainFacet[iScroll].length)){
        facetPos += (height.xaxis[iScroll]/numFacets)
      }
      //facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + ((height.yaxis[iScroll])*(vFacet['y'].length/numYvalues)) + yaxis.offset.bottom + ((xaxis.rangeScroll == 'free')? height.xaxis[iScroll][iFacet]: 0);
    })

    height.facet[iScroll] += d3.sum(height.facetLabel[iScroll]);
  })
  //console.log('height.facetLabel', height.facetLabel)
  //console.log('height.facet', height.facet)
  //console.log('facet_ypos', facet_ypos)





  // --- Margins of Column Data  --->
  margin.column_before_x = 0;
  if(column_data.before_x != null){

    dataPlot.forEach(function(vScroll, iScroll){
      vScroll.forEach(function(vFacet, iFacet){
        vFacet.forEach(function(vSwitcher, iSwitcher){
          vSwitcher.forEach(function(vObs, iObs){

            if(vObs[column_data.before_x['var']] != null){
              var text_val = ((column_data.before_x['prefix'] != null)?column_data.before_x['prefix']:'') + ((column_data.before_x['var'] != null)?(d3.format(column_data.before_x['format'])(vObs[column_data.before_x['var']])): '') + ((column_data.before_x['suffix'] != null)?column_data.before_x['suffix']:'');
            }
            else{
              var text_val = ''
            }

            margin.column_before_x = Math.max(margin.column_before_x, textWidth(text_val, column_data.before_x.size, column_data.before_x.weight)+10)

          })
        })
      })
    })

  }
  //console.log('margin.column_before_x', margin.column_before_x)


  margin.column_after_x = 0;
  if(column_data.after_x != null){

    dataPlot.forEach(function(vScroll, iScroll){
      vScroll.forEach(function(vFacet, iFacet){
        vFacet.forEach(function(vSwitcher, iSwitcher){
          vSwitcher.forEach(function(vObs, iObs){

            if(vObs[column_data.after_x['var']] != null){
              var text_val = ((column_data.after_x['prefix'] != null)?column_data.after_x['prefix']:'') + ((column_data.after_x['var'] != null)?(d3.format(column_data.after_x['format'])(vObs[column_data.after_x['var']])): '') + ((column_data.after_x['suffix'] != null)?column_data.after_x['suffix']:'');
            }
            else{
              var text_val = ''
            }

            margin.column_after_x = Math.max(margin.column_after_x, textWidth(text_val, column_data.after_x.size, column_data.after_x.weight)+10);

          })
        })
      })
    })

  }
  // <--- Margins of Column Data  ---






  // Height of column data labels
  height.label_before_x = 0;
  if(column_data.before_x != null && column_data.before_x.label.value != null){
    height.label_before_x =  column_data.before_x.label.padding.top + column_data.before_x.label.padding.bottom + (column_data.before_x.label.size*1.1)*splitWrapText(column_data.before_x.label.value, margin.column_before_x, column_data.before_x.label.size, column_data.before_x.label.weight, font.family).length
  }

  height.label_after_x = 0;
  if(column_data.after_x != null && column_data.after_x.label.value != null){
    height.label_after_x =  column_data.after_x.label.padding.top + column_data.after_x.label.padding.bottom + (column_data.after_x.label.size*1.1)*splitWrapText(column_data.after_x.label.value, margin.column_after_x, column_data.after_x.label.size, column_data.after_x.label.weight, font.family).length
  }

  height.column_data_label = Math.max(height.label_before_x, height.label_after_x)
  //console.log('height.column_data_label', height.column_data_label)






  // Calculate height of each Scroll
  height.scrollFace = []
  height.facet.forEach(function(vScroll, iScroll){

    height.scrollFace[iScroll] = height.column_data_label + d3.sum(height.facetLabel[iScroll]) + height.yaxis[iScroll] + ((yaxis.offset.top + yaxis.offset.bottom)*height.facetLabel[iScroll].length) + height.xaxis[iScroll] + height.xaxisLabel[iScroll]

  })
  //console.log('height.scrollFace:', height.scrollFace)




  // Calculate width needed for text on bars
  margin.bar_text = 0;
  if(barmode == 'group' || barmode == 'overlay'){

    dataPlot.forEach(function(vScroll, iScroll){
      vScroll.forEach(function(vFacet, iFacet){
        vFacet.forEach(function(vSwitcher, iSwitcher){

            bar.text.forEach(function(vBarText, iBarText){

              var text_val_prefix = (vBarText['prefix'] != null)? vBarText['prefix']: '';
              var text_val_main = (vBarText['format'] != null)? d3.format(vBarText['format'])(vSwitcher[vBarText['var']]): vSwitcher[vBarText['var']];
              var text_val_suffix = (vBarText['suffix'] != null)? vBarText['suffix']: '';
              var text_val = text_val_prefix + text_val_main + text_val_suffix;

              margin.bar_text = Math.max(margin.bar_text, textWidth(text_val, bar.size, bar.weight)+10);
            })

        })
      })
    })

  }





  // Canvas Height
  canvas.height = margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace) + margin.bottom ;

  /*console.log('margin.top', margin.top)
  console.log('height.title', height.title)
  console.log('height.scroll', height.scroll)
  console.log('height.switcher', height.switcher)
  console.log('height.legend', height.legend)
  console.log('d3.max(height.scrollFace)', d3.max(height.scrollFace))
  console.log('margin.bottom', margin.bottom)
  console.log('canvas.height', canvas.height)*/

  // <------------------------
  // <----- Graph Sizing -----
  // <------------------------











  // ----- Change height of parent DIV ----->
  /*d3.select(html_id)
    .style('height', (canvas.height + 10) + 'px') ;*/

  // ----- Create SVG element ----->
  var svg = d3.select(html_id)
      .append("div")
      .classed("svg-container", true)
      .append("svg")
      .attr("preserveAspectRatio", "xMinYMin meet")
      .attr("viewBox", "0 0 " + canvas.width + " " + canvas.height)
      .classed("svg-content", true)
      .append('g');


  if(y.highlight.var != null){
    var svg_g = svg.append('g').on('mouseover', (event, v) => {
          g_highlight.transition()
            .duration(500)
            .attr('transform', `translate(${canvas.width}, ${0})`);
    })
  }
  else{
    var svg_g = svg.append('g');
  }

      /*d3.select(html_id)
      .append("svg")
      .attr('width', canvas.width)
      .attr('height', canvas.height)
      //.attr("viewBox", [-canvas.width/2, -canvas.height/2, canvas.width, canvas.height])
      //.attr("style", "max-width: 100%; height: auto; height: intrinsic;");*/





  // ----------------->
  // ----- TITLE ----->
  // ----------------->

  // Group
  var g_title = svg_g.append('g')
    .attr('class', "g_title")
    .attr('transform', `translate(${margin.left}, ${margin.top})`);


  //  Title Text
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
  var g_scroll = svg_g.append('g')
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
              .append('text')
                .attr('class', "scroll_text_" + iScroll)
                .attr('opacity', function(){ return 1 - Math.min(iScroll, 1) })
                .style('font-family', font.family)
                .style('font-size', scroll.size +  'px')
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
  var g_switcher = svg_g.append('g')
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
              .style('dominant-baseline', 'hanging')
              .attr('x', 0)
              .attr('dy', function(d, i){ return i*1.1 + 'em'})
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

                changeBars(event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1] )

          })
          .on("mouseover", function(d) {
              d3.select(this).style("cursor", "pointer");
          });


    switcherGroup.append("rect")
      .attr('class', function(d, i){ return 'switcher_' + i})
      .attr('width-value', d => d['width-value'])
      //.attr('x', d => 0 - (d['width-value']/2))
      //.attr('x', -5)
      .attr('x', 5)
      .attr('y', -3)
      .attr('width', d => d['width-value']-8)
      .attr('height', d => (d['text'].length*(switcher.size*1.1)) + 6)
      .attr('fill', '#d3d2d2');


    switcherGroup.append('text')
      .attr('class', function(d, i){ return 'switcher_' + i})
      .style('font-family', font.family)
      .style('font-size', switcher.size +  'px')
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
          //.attr('x', d => (d['max-width-value'] - d['this-width-value'])/2) // Centre-align horizontally
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
  var g_legend = svg_g.append('g')
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
                .style('dominant-baseline', 'hanging')
                .attr('x', 0)
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
      }

      // --- Legend with Colored Rectangles --->
      var legend_rect = g_legend.selectAll('.legend')
        .data(legendText.filter(d => d['type'] == 'rect'))
        .enter()
        .append('g')
          .attr('class', function(d, i){ return "legend_" + i})
          //.attr('transform', function(d){ return `translate(${d['x']}, ${d['y']})` })
          .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
          .attr('opacity', 1.0)
          .on('click', (event, v) => {

                if(+event.currentTarget.getAttribute('opacity') == 1){
                    svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 0.2);
                    //svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('opacity', 0);
                    svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('visibility', 'hidden');
                }
                else{
                    svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 1.0);
                    //svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('opacity', 1);
                    svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('visibility', 'visible');
                    //svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).filter('.bar_rect').transition().duration(200).attr('opacity', d => d['opacity']);
                }

          })
          .on("mouseover", function(d) {
              d3.select(this).style("cursor", "pointer");
          });


      legend_rect.append('rect')
        .attr('class', function(d, i){ return "legend_" + i})
        .attr('x', 0)
        .attr('width', group.size)
        .attr('height', group.size)
        .attr('fill', d => d['color'])
        .attr('stroke-width', 1)
        .attr('stroke', function(d){
          if(d['color'] == 'white' || d['color'] == 'rgb(255,255,255)' || d['color'] == '#fff' || d['color'] == '#ffffff'){
            return '#d3d2d2'
          }
          else{
            return d['color']
          }
        });

      legend_rect.append('text')
        .attr('class', function(d, i){ return "legend_" + i})
        .style('font-family', font.family)
        .style('font-size', group.size +  'px')
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


    if(legendText.length > 0 && legendText.filter(d => d['type'] == 'line').length > 0){

        // --- Legend with Lines --->
        var legend_line = g_legend.selectAll('.legend_line')
          .data(legendText.filter(d => d['type'] == 'line'))
          .enter()
          .append('g')
            .attr('class', function(d, i){ return "legend_line_" + i})
            .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
            .attr('opacity', 1.0);


        legend_line.append('path')
          .attr('class', function(d, i){ return "legend_" + i})
          .attr('x', 0)
          .style('stroke-dasharray', function(d){
            if(d['line_style'] == 'dashed'){ return '5' }
            else if(d['line_style'] == 'dotted'){ return '2' }
            else{ return '0' }
          })
          .attr('stroke', d => d['color'])
          .attr('stroke-width', d => d['width'])
          .attr('d', 'M ' + 0 + ',' + group.size*0.5 + ' L ' + group.size + ',' + group.size*0.5 + ' Z');


        legend_line.append('text')
          .attr('class', function(d, i){ return "legend_" + i})
          .style('font-family', font.family)
          .style('font-size', group.size +  'px')
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










  // ---------------->
  // ----- AXES ----->
  // ---------------->

  // --- Y-Axis --->

  // Scale
  var yScale = [], yAxisChart = [];
  domainFacet.forEach(function(vScroll, iScroll){
    yScale[iScroll] = [];
    yAxisChart[iScroll] = [];

    var numYValuesInScroll = 0;
    vScroll.forEach(function(vFacet, iFacet){
      numYValuesInScroll += vFacet['y'].length
    })

    vScroll.forEach(function(vFacet, iFacet){

      yScale[iScroll][iFacet] = d3.scaleBand()
        .domain(vFacet['y'])
        .range([
          yaxis.offset.top,
          yaxis.offset.top + (height.yaxis[iScroll]*(vFacet['y'].length/numYValuesInScroll))
        ])
        .padding([0.10]);

      // Axis
      yAxisChart[iScroll][iFacet] = d3.axisLeft(yScale[iScroll][iFacet]);
    })
  })

  // <--- Y-Axis ---





  // --- X-Axis --->
  var xScale = [];
  var xAxisChart = [];
  //height.xaxis = [];


  domainFacet.forEach(function(vScroll, iScroll){
    xScale[iScroll] = [];
    xAxisChart[iScroll] = [];
    //height.xaxis[iScroll] = [];

    vScroll.forEach(function(vFacet, iFacet){

      // Scale
      var minXvalue = Infinity;
      var maxXvalue = -Infinity;

      if(xaxis.rangeFacet == 'free' && xaxis.rangeScroll == 'free'){

          dataPlot[iScroll][iFacet].forEach(function(vSwitcherData, iSwitcherData){
            vSwitcherData.forEach(function(vData, iData){
              minXvalue = Math.min(minXvalue, vData['startRect']);
              maxXvalue = Math.max(maxXvalue, vData['endRect']);
            })
          })

      }
      else if(xaxis.rangeFacet == 'free' && xaxis.rangeScroll == 'fixed'){

          dataPlot[iScroll].forEach(function(vFacetData, iFacetData){
            vFacetData.forEach(function(vSwitcherData, iSwitcherData){
              vSwitcherData.forEach(function(vData, iData){
                minXvalue = Math.min(minXvalue, vData['startRect']);
                maxXvalue = Math.max(maxXvalue, vData['endRect']);
              })
            })
          })

      }
      else if(xaxis.rangeFacet == 'fixed' && xaxis.rangeScroll == 'free'){

          dataPlot.forEach(function(vScrollData, iScrollData){
            vScrollData.forEach(function(vFacetData, iFacetData){
              vFacetData.forEach(function(vSwitcherData, iSwitcherData){
                vSwitcherData.forEach(function(vData, iData){
                  minXvalue = Math.min(minXvalue, vData['startRect']);
                  maxXvalue = Math.max(maxXvalue, vData['endRect']);
                })
              })
            })
          })

      }
      else{

          dataPlot.forEach(function(vScrollData, iScrollData){
            vScrollData.forEach(function(vFacetData, iFacetData){
              vFacetData.forEach(function(vSwitcherData, iSwitcherData){
                vSwitcherData.forEach(function(vData, iData){
                  minXvalue = Math.min(minXvalue, vData['startRect']);
                  maxXvalue = Math.max(maxXvalue, vData['endRect']);
                })
              })
            })
          })

      }

      var xScaleDomain = [
        (xaxis.range[0] != null)? xaxis.range[0]: minXvalue,
        (xaxis.range[1] != null)? xaxis.range[1]: maxXvalue
      ]
      if (!x.ascending){ xScaleDomain.reverse() }


      xScale[iScroll][iFacet] = d3.scaleLinear()
      .domain(xScaleDomain)
      .range([
        margin.yaxisLabel[iScroll] + margin.yaxis[iScroll] + margin.column_before_x + xaxis.offset.left,
        canvas.width - (margin.left + xaxis.offset.right + margin.right + margin.bar_text + margin.column_after_x)
      ]);



      // Axis
      xAxisChart[iScroll][iFacet] = d3.axisBottom()
      .scale(xScale[iScroll][iFacet])
      //.tickFormat((d) => (xaxis.suffix != null)? (d + xaxis.suffix): d);
      .tickFormat((d) => (xaxis.suffix != null)? (((xaxis.format) != null? d3.format(xaxis.format)(d): d) + xaxis.suffix): ((xaxis.format) != null? d3.format(xaxis.format)(d): d) );




      if(xaxis.num_ticks != null){
        xAxisChart[iScroll][iFacet].ticks(xaxis.num_ticks)
      }
      if(xaxis.show_grid){
        //xAxisChart[iScroll][iFacet].tickSize(-(height.yaxis[iScroll] + height.facet[iScroll] + yaxis.offset.bottom));
        xAxisChart[iScroll][iFacet].tickSize(-((yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0])  + yaxis.offset.bottom));
      }


      /*
      // Calculate maximum x-axis height for all facets within all scrolls
      height.xaxis[iScroll][iFacet] = 0;

      if(xaxis.show && xaxis.show_ticks){
        height.xaxis[iScroll][iFacet] = 20;

        if(xaxis.tick.orientation == 'v'){

          xAxisChart[iScroll][iFacet].scale().ticks().forEach(function(vXtick, iXtick){

              splitWrapText((xaxis.format != null)? d3.format(xaxis.format)(vXtick): vXtick, width=xaxis.tick.splitWidth, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).forEach(function(vXtickSplit, iXtickSplit){
                height.xaxis[iScroll][iFacet] = Math.max(
                  height.xaxis[iScroll][iFacet],
                  20 + textWidth(vXtickSplit, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family)
                )
              })

          })

        }
        else{

          xAxisChart[iScroll][iFacet].scale().ticks().forEach(function(vXtick, iXtick){
              height.xaxis[iScroll][iFacet] = Math.max(
                height.xaxis[iScroll][iFacet],
                20 + ((xaxis.tick.size*1.1)*splitWrapText((xaxis.format != null)? d3.format(xaxis.format)(vXtick): vXtick.toString(), width=xaxis.tick.splitWidth, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).length)
              )
          })

        }
      }
      */

    })

  })

  // <--- X-Axis ---





  // --- Scale for shifting bars up/down Y-Axis bandwidth --->

  var barShiftScale = d3.scaleLinear()
    .domain([
      0,
      domainGroup.length-1
    ])
    .range([
      -((domainGroup.length-1)*(height.bar/2)),
      (domainGroup.length-1)*(height.bar/2)
    ]);

  // <--- Scale for shifting bars up/down Y-Axis bandwidth ---

  // <----------------
  // <----- AXES -----
  // <----------------










  // ----------------->
  // ----- CHART ----->
  // ----------------->

  // ----- Group ----->
  var g_chart = svg_g.append("g").attr("class", "g_chart");



  dataPlot.forEach(function(vScroll, iScroll){

      // ----- Group ----->
      var g_scroll = g_chart.append('g')
        .attr('class', "g_scroll_" + iScroll)
        .attr('opacity', d => 1 - Math.min(iScroll, 1))
        .attr('x', canvas.width*iScroll)
        .attr('transform', function(d, i){
          return `translate(${((canvas.width*Math.min(1, iScroll)) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
        });
      // <----- Group -----





      // --- Add Y-Axis Label to plot --->
      if(yaxis.label.value != null){
          g_scroll.append('text')
            .attr('class', 'yAxisLabel')
            .style('font-family', font.family)
            .style('font-size', yaxis.label.size + 'px')
            .style('font-weight', yaxis.label.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', 'hanging')
            .attr('x', function(d){
              if(facet.var != null){ return -(height.scrollFace[iScroll]*0.5) }
              else{ return -(height.column_data_label + yaxis.offset.top + (height.yaxis[iScroll]*0.5))}
            }) // Moves vertically (due to rotation)
            .attr('y', 0) // Moves horizontally (due to rotation)
            .attr('transform', "rotate(-90)")
            .text(yaxis.label.value)
            .call(splitWrapTextSpan, height.yaxis0[iScroll], yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
      }
      // <--- Add Y-Axis Label to plot ---





      // ----- Before/After X-Axis Column Labels ----->

      var g_column_data_label = g_scroll.append('g')
        .attr('class', 'g_column_data_label')
        //.attr('transform', `translate(${0}, ${0})`);

      if(column_data.before_x != null && column_data.before_x.label.value != null){

        g_column_data_label.selectAll('label_before_x_' + iScroll)
          .data(splitWrapText(column_data.before_x.label.value, margin.column_before_x, fontSize=column_data.before_x.label.size, fontWeight=column_data.before_x.label.weight, fontFamily=font.family))
          .enter()
          .append('text')
            .attr('class', 'label_before_x_' + iScroll)
            .style('font-family', font.family)
            .style('font-size', column_data.before_x.label.size + 'px')
            .style('font-weight', column_data.before_x.label.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', 'middle')
            .attr('opacity', 1.0)
            .attr('visibility', 'visible')
            .attr('fill', function(d){
              if(column_data.before_x['color'].value != null){ return column_data.before_x['color'].value; }
              else{ return 'black'; }
            })
            .attr('x', xScale[iScroll][0].range()[0] - (margin.column_before_x*0.5))
            .attr('dy', function(d, i){ return i*1.1 + 'em'})
            .attr('transform', `translate(${0}, ${column_data.before_x.label.padding.top})`)
            .text(d => d);

      }

      if(column_data.after_x != null && column_data.after_x.label.value != null){

        g_column_data_label.selectAll('label_after_x_' + iScroll)
          .data(splitWrapText(column_data.after_x.label.value, margin.column_after_x, fontSize=column_data.after_x.label.size, fontWeight=column_data.after_x.label.weight, fontFamily=font.family))
          .enter()
          .append('text')
            .attr('class', 'label_after_x_' + iScroll)
            .style('font-family', font.family)
            .style('font-size', column_data.after_x.label.size + 'px')
            .style('font-weight', column_data.after_x.label.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', 'middle')
            .attr('opacity', 1.0)
            .attr('visibility', 'visible')
            .attr('fill', function(d){
              if(column_data.after_x['color'].value != null){ return column_data.after_x['color'].value; }
              else{ return 'black'; }
            })
            .attr('x', canvas.width - (margin.left + xaxis.offset.right + margin.right) - (margin.column_after_x*0.5) )
            .attr('y', column_data.after_x.label.padding.top )
            .attr('dy', function(d, i){ return i*1.1 + 'em'})
            .text(d => d);

      }

      // <----- Before/After X-Axis Column Labels -----





      vScroll.forEach(function(vFacet, iFacet){

        var g_facet = g_scroll.append('g')
          .attr('class', 'facet_' + iFacet)
          .attr('transform', `translate(${0}, ${facet_ypos[iScroll][iFacet] + height.column_data_label})`)





        // --- Add line above Facet --->
        if(facet.line.show){
          g_facet.append('path')
            .attr('d', 'M' + margin.yaxisLabel[iScroll] + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)))
            .attr('stroke', (facet.line.color != null)? facet.line.color: 'black')
            .attr('stroke-width', '2')
        }
        // <--- Add line above Facet ---











        // --- Add Y-Axis to plot --->
        if(yaxis.show){
          var y_axis_chart = g_facet.append('g')
              .attr('class', 'y_axis')
              .style('font-size', yaxis.tick.size + 'px')
              .style('font-weight', yaxis.tick.weight)
              .attr('transform', "translate(" + (margin.yaxisLabel[iScroll]+margin.yaxis[iScroll]) + "," + 0 + ")")
              .call(yAxisChart[iScroll][iFacet]);


          if(yaxis.widthPct.cutText != undefined && yaxis.widthPct.cutText){
            y_axis_chart.selectAll(".tick")
                .attr('y', '0.0')
                .attr('text_long', function(d){
                    var text = d3.select(this);
                    return text.text();
                  })
                  .attr('scroll', iScroll)
                  .attr('facet', iFacet)
                  .attr('y-value', function(d){
                    return(+d3.select(this).attr('transform').split(',')[1].split(')')[0])
                  })

            y_axis_chart.selectAll(".tick text")
                .attr('y', '0.0')
                  .call(shortenTextSpan, (((canvas.width-(margin.left+margin.right))*yaxis.widthPct.value) - margin.yaxisLabel[iScroll] - 9), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);


            y_axis_chart.selectAll(".tick")
            .on('mouseover', (event, d) => {
                      // --- Tooltip --->
                      var thisScroll = +event.currentTarget.getAttribute('scroll');
                      var thisFacet = +event.currentTarget.getAttribute('facet');

                      var text_for_tooltip = splitWrapText(event.currentTarget.getAttribute('text_long'), width=canvas.width - (margin.left+margin.right+margin.yaxisLabel[thisScroll]+margin.yaxis[thisScroll]), fontSize=yaxis.tick.size, fontWeight=yaxis.tick.weight, fontFamily=font.family)

                      var thisX = margin.left + margin.yaxisLabel[thisScroll] + margin.yaxis[thisScroll];
                      var thisY = +event.currentTarget.getAttribute('y-value') + (margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label) + facet_ypos[thisScroll][thisFacet];

                      var maxTextWidth = 0;
                      var rectHeight = 0;
                      var hoverText = [];

                      text_for_tooltip.forEach(function(vHover, iHover){
                        if((rectHeight + (yaxis.tick.size*1.1)) < (canvas.height-(margin.top+margin.bottom))){

                          hoverText.push({
                            'value': vHover.replace('<br>', ' ').replace('\n', ' '),
                            'size': yaxis.tick.size,
                            'weight': yaxis.tick.weight
                          })

                          rectHeight += (yaxis.tick.size*1.1);
                          maxTextWidth = (textWidth(vHover, yaxis.tick.size, yaxis.tick.weight) > maxTextWidth)? textWidth(vHover, yaxis.tick.size, yaxis.tick.weight): maxTextWidth;
                        }
                      })

                      maxTextWidth = Math.max(maxTextWidth, margin.yaxis[thisScroll])
                      thisX += (maxTextWidth*0.5);
                      if(((thisY-3)+rectHeight) > (canvas.height-margin.bottom)){
                        thisY -= (((thisY-3)+rectHeight) - (canvas.height-margin.bottom))
                      }




                      if((thisX + (maxTextWidth*0.5) + 5) > (canvas.width - margin.right)){
                        var shift_left = Math.abs((canvas.width - margin.right) - (thisX + (maxTextWidth*0.5) + 5))
                      };

                      g_tooltip.style('visibility', 'visible')
                          .attr('transform', `translate(${(thisX-(shift_left || 0))}, ${(Math.max(0+margin.top, thisY-3))})`);

                      tooltipRect.attr('stroke', '#d3d2d2')
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

                      // <--- Tooltip ---
            })
            .on('mouseout', (event, v) => {
                    g_tooltip.style('visibility', 'hidden').attr('transform', "translate(" + 0 + "," + 0 +")");

                    if(x.ci[0] != null && x.ci[1] != null){
                      g_data.transition()
                        .duration(0)
                        .attr('opacity', 1.0)
                    }
            });

          }
          else{
            y_axis_chart.selectAll(".tick text")
                .attr('y', '0.0')
                .call(splitWrapTextSpan, (((canvas.width-(margin.left+margin.right))*yaxis.widthPct.value) - margin.yaxisLabel[iScroll] - 9), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);
          }


          // Remove Axis Line
          if(!yaxis.show_line){
            y_axis_chart.select('.domain').remove();
          }

          // Remove Axis Ticks
          if(!yaxis.show_ticks){
            y_axis_chart.selectAll('.tick').selectAll('line').remove();
          }
        }
        // <--- Add Y-Axis to plot ---




        // --- Add X-Axis to plot --->
        //if(xaxis.show && (xaxis.rangeScroll == 'free' || (xaxis.rangeScroll == 'fixed' && (iFacet+1) == domainFacet[iScroll].length) )){
        if(xaxis.show && (xaxis.rangeScroll == 'free' || (xaxis.rangeScroll == 'fixed' && xaxis.show_grid) )){
          var x_axis_chart = g_facet.append('g')
              .attr('class', 'x_axis')
              .style('font-size', xaxis.tick.size + 'px')
              .attr('transform', "translate(" + 0 + "," + (yaxis.offset.top + (yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0]) + yaxis.offset.bottom) + ")")
              .call(xAxisChart[iScroll][iFacet]);


          /*
          x_axis_chart.selectAll(".tick text")
              .attr('x', '0.0')
              .call(splitWrapTextSpan, xaxis.tick.splitWidth, xaxis.tick.size, xaxis.tick.weight, font.family, valign='bottom', dy_extra=0.7);
          */


          // --- Tick rotation --->
          /*
          if(xaxis.tick.orientation == 'v'){

            x_axis_chart.selectAll('text')
            .style('text-anchor', 'end')
            .attr("transform", 'rotate(-90)');

            x_axis_chart.selectAll('text').selectAll('tspan')
            .style('dominant-baseline', 'middle')
            .attr('dx', "-.8em")

            x_axis_chart.selectAll('text').selectAll('tspan').each((d,i,nodes) => {
                nodes[i].setAttribute('dy', parseFloat(nodes[i].getAttribute('dy')) - (0.55 + ((1.1*nodes.length)/2)) + 'em');
                //nodes[i].setAttribute('dy', '-0.5em');
            });

          }
          */
          // <--- Tick rotation ---


          // Remove Axis Line
          if(!xaxis.show_line || (xaxis.rangeScroll == 'fixed' && (iFacet+1) != domainFacet[iScroll].length)){
            x_axis_chart.select('.domain').remove();
          }

          // Remove Axis Ticks
          if(!xaxis.show_ticks || (xaxis.rangeScroll == 'fixed' && !xaxis.show_grid)){
            x_axis_chart.selectAll('.tick').selectAll('line').remove();
          }

          // Remove Axis Tick Text
          if(xaxis.rangeScroll == 'fixed' && (iFacet+1) != domainFacet[iScroll].length){
            x_axis_chart.selectAll('.tick').selectAll('text').remove();
          }

          if(xaxis.show_grid){
            x_axis_chart.selectAll(".tick line").attr('stroke', '#d3d2d2');
          }
        }
        // <--- Add X-Axis to plot ---





        // --- Add X-Axis Label to plot --->
        if(xaxis.label.value != null && (iFacet+1) == domainFacet[iScroll].length){
            g_facet.append('text')
              .attr('class', 'xaxis_label')
              .style('font-family', font.family)
              .style('font-size', xaxis.label.size + 'px')
              .style('font-weight', xaxis.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('x', xScale[iScroll][0].range()[0] + ((xScale[iScroll][0].range()[1] - xScale[iScroll][0].range()[0])*0.5) )
              //.attr('y', yaxis.offset.top + (yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0]) + yaxis.offset.bottom + height.xaxis[iScroll])
              .attr('y', yaxis.offset.top + (yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0]) + yaxis.offset.bottom + ((facet.var != null && xaxis.rangeScroll == 'free')? (height.xaxis[iScroll]/domainFacet[iScroll].length): height.xaxis[iScroll]))
              //.attr('y', yaxis.offset.top + (yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0]) + yaxis.offset.bottom + height.xaxisLabel[iScroll])
              .text(xaxis.label.value)
              .call(splitWrapTextSpan, (xScale[iScroll][0].range()[1] - xScale[iScroll][0].range()[0]), xaxis.label.size, xaxis.label.weight, font.family, valign='bottom', dy_extra=0);
        }
        // <--- Add X-Axis Label to plot ---




        // --- Facet Title --->
        if(facet.var != null){

          var numLines_thisFacetTitle = splitWrapText(domainFacet[iScroll][iFacet]['facet'], (canvas.width - margin.left - margin.yaxisLabel[iScroll] - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length

          g_facet.selectAll('facet_text')
              .data(splitWrapText(domainFacet[iScroll][iFacet]['facet'], (canvas.width - margin.left - margin.yaxisLabel[iScroll] - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .style('font-family', font.family)
                .style('font-size', facet.size +  'px')
                .style('font-weight', facet.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('class', "facet_text")
                .attr('x', margin.yaxisLabel[iScroll] + ((canvas.width - margin.left - margin.yaxisLabel[iScroll] - margin.right)/2))
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .attr('transform', `translate(${0}, ${-height.facetLabel[iScroll][iFacet] + facet.space_above_title})`)
                .text(d => d);

        }
        // <--- Facet Title ---





        // --- Add Bars, CI and Text to plot --->
        vFacet[0].forEach(function(vSwitcher, iSwitcher){

            var g_data = g_facet.selectAll('.bar_rect')
              .data(vFacet[0])
              .enter()
              .append('g')
                .attr('class', function(d, i){
                  return 'scroll_' + iScroll +
                  ' switcher_0' +
                  ' facet_' + iFacet +
                  ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                  ' obs_' + iScroll + '_0_' + iFacet + '_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i  +
                  ' yval yval_' + domainY.indexOf(d['y'])
                })
                .attr('startRect', d => xScale[iScroll][iFacet](d['startRect']))
                .attr('endRect', d => xScale[iScroll][iFacet](d['endRect']))
                .attr('widthRect', d => xScale[iScroll][iFacet](d['endRect']) - xScale[iScroll][iFacet](d['startRect']))
                .attr('color-value', function(d){
                   if(clr.var != null){ return d['_clr'] }
                   else if(clr.value != null){ return clr.value }
                   else{ return '#e32726' }
                 })
                .attr('group-value', function(d){
                  if(group.var != null){ return d['group'] }
                  else{ return null }
                })
                .attr('x-value', d => d['x'])
                .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                .attr('y-value', function(d, i){
                  //if(barmode == 'group'){ return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) }
                  if(barmode == 'group'){ return yScale[iScroll][iFacet](d['y']) + (height.bar*(domainGroup.map(d => d['group']).indexOf(d['group']))) }
                  else{ return yScale[iScroll][iFacet](d['y']) }
                })
                .attr('opacity', 1.0)
                .attr('visibility', 'visible')
                .on('mouseover', (event, d) => {

                    if(event.currentTarget.getAttribute('visibility') == 'visible'){

                          // --- Tooltip --->
                          var thisX = +event.currentTarget.getAttribute('startRect') + (+event.currentTarget.getAttribute('widthRect')/2) + margin.left;
                          var thisY = +event.currentTarget.getAttribute('y-value') + (margin.top + height.title + height.scroll + height.switcher + height.legend + height.column_data_label);


                          var maxTextWidth = 0;
                          var rectHeight = 0;
                          var hoverText = [];


                          if(tooltip_text != null){
                            var scrollIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[1]
                            var facetIndex = event.currentTarget.getAttribute('class').split(' ')[2].split('_')[1]
                            var switcherIndex = event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]
                            var obsIndex = event.currentTarget.getAttribute('class').split(' ')[4].split('_')[5]

                            thisY += facet_ypos[scrollIndex][facetIndex]

                            var dataPoint = dataPlot[scrollIndex][facetIndex][switcherIndex][obsIndex]

                            tooltip_text.forEach(function(vTooltipLine, iTooltipLine, aTooltipLine){
                              var val = '';

                              vTooltipLine['text'].forEach(function(vTooltipLineText, iTooltipLineText){
                                val = val.concat(
                                  ((vTooltipLineText['prefix'] != null)?vTooltipLineText['prefix']:'') + ((vTooltipLineText['var'] != null)?((vTooltipLineText['format'] != null)? d3.format(vTooltipLineText['format'])(dataPoint[vTooltipLineText['var']]): dataPoint[vTooltipLineText['var']]): '') + ((vTooltipLineText['suffix'] != null)?vTooltipLineText['suffix']:'')
                                )
                              })

                              splitWrapText(text=val, width=canvas.width - (margin.left + margin.right), fontSize=vTooltipLine.size, fontWeight=vTooltipLine.weight, fontFamily=font.family).forEach(function(vVal, iVal){
                                  maxTextWidth = Math.max(maxTextWidth, textWidth(vVal, vTooltipLine.size, vTooltipLine.weight)); //(textWidth(val, vTooltipLine.size, vTooltipLine.weight) > maxTextWidth)? textWidth(val, vTooltipLine.size, vTooltipLine.weight): maxTextWidth;
                                  rectHeight += (vTooltipLine.size*1.1);

                                  hoverText.push({
                                    'value': vVal.replace('<br>', ' ').replace('\n', ' '),
                                    'size': vTooltipLine.size,
                                    'weight': vTooltipLine.weight
                                  });
                              })

                            })
                          }
                          else{
                            hoverText.push(event.currentTarget.getAttribute('x-value'));

                            rectHeight += (yaxis.tick.size*1.1);
                            maxTextWidth = (textWidth(event.currentTarget.getAttribute('x-value'), yaxis.tick.size, yaxis.tick.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute('x-value'), yaxis.tick.size, yaxis.tick.weight): maxTextWidth;
                          }




                          if((thisX + (maxTextWidth*0.5) + 5) > (canvas.width - margin.right)){
                            var shift_left = Math.abs((canvas.width - margin.right) - (thisX + (maxTextWidth*0.5) + 5))
                          };
                          if((thisX - ((maxTextWidth*0.5) + 5)) < margin.left){
                            var shift_right = Math.abs(margin.left - (thisX - ((maxTextWidth*0.5) + 5)))
                          };

                          // Put tooltip below bar if there is not enough height above the bar to fit it all in
                          if(rectHeight > thisY){
                            thisY = thisY+6+(height.bar*1.1)
                          }
                          else{
                            thisY = thisY-rectHeight-3
                          }

                          g_tooltip.style('visibility', 'visible')
                              .attr('transform', `translate(${(thisX - (shift_left || 0) + (shift_right || 0))}, ${(Math.max(0+margin.top, thisY))})`);

                          tooltipRect.attr('stroke', function(){
                              if(event.currentTarget.getAttribute('color-value') == 'white' || event.currentTarget.getAttribute('color-value') == 'rgb(255,255,255)' || event.currentTarget.getAttribute('color-value') == '#fff' || event.currentTarget.getAttribute('color-value') == '#ffffff'){
                                return '#d3d2d2'
                              }
                              else{
                                return event.currentTarget.getAttribute('color-value')
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

                          // <--- Tooltip ---



                          // --- CI Function --->
                          if(x.ci[0] != null && x.ci[1] != null){
                            var thisScroll     = +event.currentTarget.getAttribute('class').split(' ')[0].split('_')[1];
                            var thisSwitcher   = +event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1];
                            var thisFacet      = +event.currentTarget.getAttribute('class').split(' ')[2].split('_')[1];
                            var thisGroup      = +event.currentTarget.getAttribute('class').split(' ')[3].split('_')[1];
                            var thisGroupValue = event.currentTarget.getAttribute('group-value');
                            var thisObs        = event.currentTarget.getAttribute('class').split(' ')[4].split('_')[5];
                            var thisCIL        = event.currentTarget.getAttribute('cil-value');
                            var thisCIU        = event.currentTarget.getAttribute('ciu-value');
                            //console.log('thisScroll', thisScroll, 'thisSwitcher', thisSwitcher, 'thisGroup', thisGroup, 'thisObs', thisObs, 'thisXvalue', thisXvalue)

                            g_data.transition()
                              .duration(0)
                              .attr('opacity', 0.2)

                            var highlightBar = '.' + event.currentTarget.getAttribute('class').split(' ')[4];

                            dataPlot[thisScroll][thisFacet][thisSwitcher].forEach(function(vObs, iObs){
                                if((vObs['x_ci_u'] < thisCIL) || (vObs['x_ci_l'] > thisCIU)){
                                  highlightBar = highlightBar.concat(',.obs_' + thisScroll + '_' + thisSwitcher + '_' + thisFacet + '_' + thisGroup + '_'+ iObs);
                                }
                            })

                            svg.selectAll(highlightBar)
                            .transition()
                              .duration(0)
                              .attr('opacity', 1.0);
                          }

                          // <--- CI Function ---
                      }

                })
                .on('mouseout', (event, v) => {
                        g_tooltip.style('visibility', 'hidden').attr('transform', "translate(" + 0 + "," + 0 +")");

                        if(x.ci[0] != null && x.ci[1] != null){
                          g_data.transition()
                            .duration(0)
                            .attr('opacity', 1.0)
                        }
                });



            // --- Add Bars --->
            g_data.append('rect')
                .attr('class', function(d){
                  return 'bar_rect group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                })
                .attr('fill', d => d['_clr'])
                .attr('stroke-width', 1)
                .attr('stroke', d => d['_stroke_clr'])
                .attr('x-value', d => d['x'])
                .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                .attr('x', function(d){ return xScale[iScroll][iFacet](d['startRect']) })
                .attr('y', function(d, i){
                  if(barmode == 'group'){
                    return (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (rectHeightScale(d['heightPctRect'])/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) //(height.bar/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                  }
                  else{
                    return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (rectHeightScale(d['heightPctRect'])/2) //(height.bar/2)
                  }
                })
                .attr('width', function(d){ return 0 })
                .attr('height', function(d){
                  return rectHeightScale(d['heightPctRect']) //height.bar*d['heightPctRect'] //height.bar*rectHeightScale(d['heightPctRect'])
                })
                .attr('opacity', d => d['opacity'])
                .attr('visibility', 'visible')
                .transition()
                .delay(function(d){ return (domainY.indexOf(d['y'])*50) })
                .duration(800)
                  .attr('width', function(d) { return xScale[iScroll][iFacet](d['endRect']) - xScale[iScroll][iFacet](d['startRect']) });
            // <--- Add Bars ---




            // --- Add CI --->
            if(x.ci[0] != null && x.ci[1] != null){
                g_data.append('path')
                    .attr('class', function(d){
                      return 'bar_ci group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                    })
                    .attr('stroke', 'black')
                    .attr('x-value', d => d['x'])
                    .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                    .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                    .attr('d', d =>
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3)  +
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) +
                    'M' + xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3) +
                    'M' + xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 5) + 'L' +  xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 5)
                    )
                    .attr('opacity', 1.0)
                    .attr('visibility', 'visible');

            }
            // <--- Add CI ---




            // --- Add text to bars --->
            if(bar.text != null){

                var g_bar_text = g_data.append('text')
                      .attr('class', function(d){
                        return 'bar_text group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                      })
                      .style('fill', function(d){
                        if(d['text_location'] == 'inside'){
                          if(lightOrDark(d['_clr']) == 'light'){ return 'black'}
                          else{ return 'white' }
                        }
                        else{ return 'black' }
                      })
                      .style('font-family', font.family)
                      //.style('font-size', d => bar.size + 'px')
                      //.style('font-size', d => (((rectHeightScale(d['heightPctRect'])/1.1)-6 >= bar.size)? bar.size: (rectHeightScale(d['heightPctRect'])/1.1)-6) + 'px')
                      .style('font-size', d => (((rectHeightScale(d['heightPctRect'])-6)/1.1) >= bar.size)? bar.size + 'px': ((rectHeightScale(d['heightPctRect'])-6)/1.1) + 'px')
                      .style('font-weight', bar.weight)
                      .style('text-anchor', d => (d['text_location'] == 'inside')? 'middle': 'start')
                      .style('dominant-baseline', 'hanging')
                      .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                      .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                      .attr('opacity', 1.0)
                      .attr('visibility', 'visible')
                      .attr('x', d => xScale[iScroll][iFacet](d['startRect']) )
                      .attr('y', function(d, i){
                        if(barmode == 'group'){
                          //return (yScale(d['y']) + (yScale.bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) + (yScale.bandwidth()*(1/(domainGroup.length*2))) )
                          return (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                        }
                        else{
                          return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2)
                        }
                      })
                      .attr('transform', d => `translate(${(d['text_location'] == 'outside')?5:0}, ${0})`)
                      .each(d => d)
                      .call(barText, iScroll, iFacet);


                svg.select('.g_scroll_' + iScroll).selectAll('.facet_' + iFacet).selectAll('.bar_text').selectAll('tspan')
                  .transition()
                  .delay(function(d){ return (domainY.indexOf(d['y'])*50) })
                  .duration(800)
                  .attr('x', function(d){
                    if(d['text_location'] == 'inside'){
                      return xScale[iScroll][iFacet](d['startRect']) + ((xScale[iScroll][iFacet](d['endRect']) - xScale[iScroll][iFacet](d['startRect']))/2)
                    }
                    else{
                      if(x.ci[1] != null){ return xScale[iScroll][iFacet](d['x_ci_u']) }
                      else{
                        return xScale[iScroll][iFacet](d['endRect'])
                      }
                    }

                  });

            }
            // <--- Add text to bars ---




            // --- Add Vertical Lines from Variable --->
            if(vline.var != null){

                var g_bar_text = g_data.append('path')
                      .attr('class', function(d){
                        if(d[vline.var['name']] != null){ return 'vline_var group_' + domainGroup.map(d => d['group']).indexOf(d['group']) }
                        else{ return 'vline_var' }
                      })
                      .style('stroke-dasharray', function(d){
                        if(vline.var['line_style'] == 'dashed'){ return '5' }
                        else if(vline.var['line_style'] == 'dotted'){ return '2' }
                        else{ return '0' }
                      })
                      .attr('opacity', function(d){
                        if(d[vline.var['name']] != null){ return '1' }
                        else{ return '0' }
                      })
                      .attr('visibility', function(d){
                        if(d[vline.var['name']] != null){ return 'visible' }
                        else{ return 'hidden' }
                      })
                      .attr('stroke', vline.var['clr'])
                      .attr('stroke-width', vline.var['width'])
                      .attr('d', function(d){return 'M ' +
                        ((d[vline.var['name']] != null)? xScale[iScroll][iFacet](d[vline.var['name']]): xScale[iScroll][iFacet].range()[0]) + ', ' +
                        ((barmode == 'group')? ((yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (height.bar/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))): (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (height.bar/2))) +
                        ' L ' +
                        ((d[vline.var['name']] != null)? xScale[iScroll][iFacet](d[vline.var['name']]): xScale[iScroll][iFacet].range()[0]) + ', ' +
                        ((barmode == 'group')? ((yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (height.bar/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + height.bar): (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) - (height.bar/2) + height.bar)) +
                        ' Z'})

            }
            // <--- Add Vertical Lines from Variable ---






            // --- Add vertical lines from set values --->
            if(vline.value != null){
              svg.select('.g_scroll_' + iScroll).select('.facet_' + iFacet).selectAll('vline_path')
                  .data(vline.value)
                  .enter()
                  .append('path')
                    .style('stroke-dasharray', function(d){
                      if(d['line_style'] == 'dashed'){ return '5' }
                      else if(d['line_style'] == 'dotted'){ return '2' }
                      else{ return '0' }
                    })
                    .attr('d', function(d){return 'M ' + xScale[iScroll][iFacet](d['x']) + ', ' + yScale[iScroll][iFacet].range()[0] + ' L ' + xScale[iScroll][iFacet](d['x']) + ', ' + yScale[iScroll][iFacet].range()[1] + ' Z'})
                    .attr('stroke', d => d['_clr'])
                    .attr('stroke-width',d => d['width'])
                    .attr('opacity', 0)
                    .attr('visibility', 'visible')
                    .transition()
                      .duration(800)
                      .attr('opacity', 1)
            }
            // <--- Add vertical lines from set values ---





            // --- Add Column Data --->

            if(column_data.before_x != null){

                  g_data.append('text')
                    .attr('class', function(d){
                      if(barmode == 'group'){ return 'column_data_before_x group_' + domainGroup.map(d => d['group']).indexOf(d['group']) }
                      else { return 'column_data_before_x' }
                    })
                    .style('font-family', font.family)
                    .style('font-size', column_data.before_x.size + 'px')
                    .style('font-weight', column_data.before_x.weight)
                    .style('text-anchor', 'end')
                    .style('dominant-baseline', 'middle')
                    .attr('opacity', 1.0)
                    .attr('visibility', 'visible')
                    .attr('fill', function(d){
                      if(column_data.before_x['color'].value != null){ return column_data.before_x['color'].value; }
                      else if(column_data.before_x['color'].var != null){ return d[column_data.before_x['color'].var]; }
                      else{ return 'black'; }
                    })
                    .attr('x', xScale[iScroll][iFacet].range()[0])
                    .attr('y', function(d, i){
                      if(barmode == 'group'){
                        return (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                      }
                      else{
                        return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2)
                      }
                    })
                    .attr('text-num', function(d){
                       if(d[column_data.before_x['var']]){
                         return d[column_data.before_x['var']]
                       }
                       else{
                         return 0;
                       }
                     })
                    .attr('text-char', function(d){
                       if(d[column_data.before_x['var']]){
                         return d[column_data.before_x['var']]
                       }
                       else{
                         return '';
                       }
                     })
                    .attr('transform', `translate(${-5}, ${0})`)
                    .text(function(d){
                      if(barmode == 'stack'){
                          if(domainGroup.map(d => d['group']).indexOf(d['group']) == 0){
                            if(d[column_data.before_x['var']] == null){ return '' }
                            else{ return ((column_data.before_x['prefix'] != null)?column_data.before_x['prefix']:'') + ((column_data.before_x['var'] != null)?(d3.format(column_data.before_x['format'])(d[column_data.before_x['var']])): '') + ((column_data.before_x['suffix'] != null)?column_data.before_x['suffix']:'') }
                          }
                          else{
                            return ''
                          }
                      }
                      else{
                        if(d[column_data.before_x['var']] == null){ return '' }
                        else{ return ((column_data.before_x['prefix'] != null)?column_data.before_x['prefix']:'') + ((column_data.before_x['var'] != null)?(d3.format(column_data.before_x['format'])(d[column_data.before_x['var']])): '') + ((column_data.before_x['suffix'] != null)?column_data.before_x['suffix']:'') }
                      }
                    })

            }



            if(column_data.after_x != null){

                  g_data.append('text')
                    .attr('class', function(d){
                      if(barmode == 'group'){ return 'column_data_after_x group_' + domainGroup.map(d => d['group']).indexOf(d['group']) }
                      else { return 'column_data_after_x' }
                    })
                    .style('font-family', font.family)
                    .style('font-size', column_data.after_x.size + 'px')
                    .style('font-weight', column_data.after_x.weight)
                    .style('text-anchor', 'start')
                    .style('dominant-baseline', 'middle')
                    .attr('opacity', 1.0)
                    .attr('visibility', 'visible')
                    .attr('fill', function(d){
                      if(column_data.after_x['color'].value != null){ return column_data.after_x['color'].value; }
                      else if(column_data.after_x['color'].var != null){ return d[column_data.after_x['color'].var]; }
                      else{ return 'black'; }
                    })
                    .attr('x', canvas.width - (margin.left + xaxis.offset.right + margin.right + margin.column_after_x) )
                    .attr('y', function(d, i){
                      if(barmode == 'group'){
                        return (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                      }
                      else{
                        return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2)
                      }
                    })
                    .attr('text-num', function(d){
                       if(d[column_data.after_x['var']]){
                         return d[column_data.after_x['var']]
                       }
                       else{
                         return 0;
                       }
                     })
                    .attr('text-char', function(d){
                       if(d[column_data.after_x['var']]){
                         return d[column_data.after_x['var']]
                       }
                       else{
                         return '';
                       }
                     })
                    .attr('transform', `translate(${5}, ${0})`)
                    .text(function(d){
                      if(barmode == 'stack'){
                          if(domainGroup.map(d => d['group']).indexOf(d['group']) == 0){
                            if(d[column_data.after_x['var']] == null){ return '' }
                            else{ return ((column_data.after_x['prefix'] != null)?column_data.after_x['prefix']:'') + ((column_data.after_x['var'] != null)?(d3.format(column_data.after_x['format'])(d[column_data.after_x['var']])): '') + ((column_data.after_x['suffix'] != null)?column_data.after_x['suffix']:'') }
                          }
                          else{
                            return ''
                          }
                      }
                      else{
                        if(d[column_data.after_x['var']] == null){ return '' }
                        else{ return ((column_data.after_x['prefix'] != null)?column_data.after_x['prefix']:'') + ((column_data.after_x['var'] != null)?(d3.format(column_data.after_x['format'])(d[column_data.after_x['var']])): '') + ((column_data.after_x['suffix'] != null)?column_data.after_x['suffix']:'') }
                      }
                    })
            }
            // <--- Add Column Data ---

        })

      })
    });

  // <-----------------
  // <----- CHART -----
  // <-----------------





  // -------------------------->
  // ----- HIGHLIGHT DATA ----->
  // -------------------------->

  if(y.highlight.var != null){

    var domainHighlight = [];

    if(y.highlight.title != null){
      domainHighlight.push(y.highlight.title)
    }

    Array.from(new Set(data.map(d => d[y.highlight.var]).flat())).forEach((v, i) => {
      domainHighlight.push(v)
    })

    //var domainHighlight = Array.from(new Set(data.map(d => d[y.highlight.var]).flat()));

    var dataPlot_highlight = [];
    domainHighlight.forEach((vHighlight, iHighlight) => {
      var g_highlight_classes = '';
      Array.from(new Set(data.filter(d => d[y.highlight.var].includes(vHighlight)).map(d => d[y.var]))).forEach(function(vY, iY){
        g_highlight_classes = g_highlight_classes.concat(' yval_' + domainY.indexOf(vY));
      });

      dataPlot_highlight.push({'highlight': vHighlight, 'classes': g_highlight_classes});
    })

    //console.log('dataPlot_highlight:', dataPlot_highlight)




    function highlightTextSize(text, fontFace=font.family, fontSize=16, fontWeight=700) {
        if (!d3) return;
        var container = d3.select('body').append('svg').attr("class", 'textSizeCalc');
        container.append('text')
          .attr('x', -99999)
          .attr('y', -99999)
          .style('font-family', fontFace)
          .style('font-size', fontSize + "px")
          .style('font-weight', fontWeight)
          .text(text);

        var size = container.node().getBBox();
        container.remove();

        return { width: size.width, height: size.height };
    }


    function idealHighlightSizes(
      data=dataPlot_highlight,
      fontFace = font.family,
      maxfontSize=yaxis.tick.size,
      requiredHeight=canvas.height - (margin.top + height.title + height.scroll + height.switcher + margin.bottom)
    ){
      // Loop down through fontsizes to find the first one that will fit all highlighs in
      var idealFontSize = maxfontSize;
      for(let fontSize = maxfontSize; fontSize > 0; fontSize--){

        idealFontSize = fontSize;

        //var numLines = 0;
        var totalHeight = 0;

        data.forEach((v, i) => {
            v['y'] = totalHeight;
            v['fontSize'] = fontSize;
            var numLines = splitWrapText(v['highlight'], width=((canvas.width*0.25)*0.9), fontSize=fontSize, fontWeight=700, fontFamily=fontFace).length;
            totalHeight += (numLines*highlightTextSize(v['highlight'], fontFace=fontFace, fontSize=fontSize).height) + highlightTextSize(v, fontFace=font.family, fontSize=fontSize).height
        })

        if (totalHeight < requiredHeight){ return idealFontSize; }
      };
    }
    var highlightFontSize = idealHighlightSizes();

    //console.log('highlightFontSize', highlightFontSize);
    //console.log('dataPlot_highlight:', dataPlot_highlight)

    // <--------------------------
    // <----- HIGHLIGHT DATA -----
    // <--------------------------





    // ----------------------------->
    // ----- HIGHLIGHT SIDEBAR ----->
    // ----------------------------->

    var g_highlight = svg.append('g')
        .attr('class', 'g_highlight')
        .attr('x', margin.left)
        .attr('y', margin.top)
        .attr('transform', `translate(${(canvas.width)}, ${0})`);



    g_highlight.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', (canvas.width*0.25))
      .attr('height', canvas.height - (margin.top + margin.bottom))
      .attr('fill', '#d3d2d2') // light gray
      /*.on('mouseout', (event, v) => {
                if(g_highlight.node().transform.baseVal.getItem(0).matrix.e < canvas.width){
                  g_highlight.transition()
                  .duration(500)
                  .attr('transform', `translate(${canvas.width}, ${0})`);
                }
      })*/
      .on('click', (event, v) => {
                d3.selectAll('.highlight_text').style('font-weight', 'normal')
                g_chart.selectAll('g').style('opacity', 1.0);
      })


    /*
    var circle_radius = canvas.width*0.015; //height.bar/2;

    g_highlight.append('circle')
      .attr('cx', 0)
      .attr('cy', height.title + circle_radius)
      .attr('r', circle_radius)
      .attr('fill', '#d3d2d2') // light gray
      .on('mouseover', (event, v) => {

            if(g_highlight.node().transform.baseVal.getItem(0).matrix.e == canvas.width){
              g_highlight.transition()
              .duration(500)
              .attr('transform', `translate(${canvas.width-(canvas.width*0.25)}, ${0})`);
            }
      })
      */

      var highlight_menu_width = (canvas.width*0.015)*2;

      var g_highlight_menu =  g_highlight.append('g')
      .on('mouseover', (event, v) => {

            if(g_highlight.node().transform.baseVal.getItem(0).matrix.e == canvas.width){
              g_highlight.transition()
              .duration(500)
              .attr('transform', `translate(${canvas.width-(canvas.width*0.25)}, ${0})`);
            }
      });

      g_highlight_menu.append('rect')
        .attr('x', -highlight_menu_width)
        .attr('y', height.title )
        .attr('fill', '#d3d2d2') // light gray
        .attr('height', highlight_menu_width)
        .attr('width', highlight_menu_width);

      g_highlight_menu.selectAll('.highlight_menu')
        .data([1, 3, 5])
          .enter()
          .append('rect')
          .attr('x', -highlight_menu_width+((1/7)*highlight_menu_width))
          .attr('y',  d => (d/7)*highlight_menu_width)
          .attr('fill', '#4d4c4c')
          .attr('rx', 2)
          .attr('ry', 2)
          .attr('height', ((1/7)*highlight_menu_width))
          .attr('width', ((5/7)*highlight_menu_width));





    g_highlight.selectAll('.highlight_text')
      .data(dataPlot_highlight)
        .enter()
        .append('g')
        .attr('class', d => d['classes'])
        .attr('transform', d => `translate(${0}, ${height.title + height.scroll + height.switcher + d['y']})` )
        //.on('mouseover', (event, v) => {
        //      g_highlight.transition()
        //        .duration(500)
        //        .attr('transform', `translate(${canvas.width-(canvas.width*0.25)}, ${0})`);
        //})
        .append('text')
          .attr('class', (d, i) => (y.highlight.title != null && i == 0)? '': 'highlight_text' + d['classes'])
          .style('font-family', font.family)
          .style('font-size', d => d['fontSize'] + 'px' )
          .style('font-weight', (d, i) => (y.highlight.title != null && i == 0)? 700: 400)
          .style('text-anchor', 'middle')
          .attr('x', (canvas.width*0.25)*0.5)
          .attr('y', 0 )
          .attr('dy', '1.1em')
          .text(d => d['highlight'])
          .call(splitWrapTextSpan, width=((canvas.width*0.25)*0.9), fontSize=highlightFontSize, fontWeight=700, fontFace=font.family, valign='bottom', dy_extra=0)
          .on("mouseover", function() {
            if(d3.select(this).attr('class').split(' ')[0] == 'highlight_text'){
              d3.select(this).style("cursor", "pointer");
            }
          })
          .on("click", function() {
            var filteredClasses = '.' + d3.select(this).attr('class').split(' ').slice(1).join(",.");

            d3.selectAll('.highlight_text').style('font-weight', '400');
            d3.select(this).style('font-weight', '700');

            // Highlight Bars
            g_chart.selectAll('.yval').style('opacity', 0.2);
            g_chart.selectAll(filteredClasses).style('opacity', 1.0);
          });




    // --- White rectangle to cover gray highlight area (to account for user zooming out) --->
    svg.append('g')
        .attr('x', margin.left)
        .attr('y', margin.top)
        .attr('transform', `translate(${(canvas.width)}, ${0})`)
          .append('rect')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', (canvas.width*0.25))
            .attr('height', canvas.height - (margin.top + margin.bottom))
            .attr('fill', 'white');
    // <--- White rectangle to cover gray highlight area (to account for user zooming out) ---
  }

  // <-----------------------------
  // <----- HIGHLIGHT SIDEBAR -----
  // <-----------------------------










  // ------------------->
  // ----- TOOLTIP ----->
  // ------------------->

  var g_tooltip = svg.append('g')
    .attr('class', "tooltip_" + html_id.slice(1))
    .style('visibility', 'hidden');

  var tooltipRect =  g_tooltip.append('rect')
      .attr('class', "tooltip_" + html_id.slice(1) + "__rect")
      .attr('x', 0)
      .attr('y', -3)
      .attr('width', 0)
      .attr('height', 0)
      .attr('fill', "white")
      .attr('stroke', "black")
      .attr('stroke-width', "2");

  var tooltipText = g_tooltip.append('text')
    .style('text-anchor', 'middle')
    .style('dominant-baseline', 'hanging')
    .attr('class', "tooltip_" + html_id.slice(1) + "__text")
    .style('font-family', font.family)
    .attr('x', 0)
    .attr('y', 0);

  // <-------------------
  // <----- TOOLTIP -----
  // <-------------------





  // ---------------->
  // ----- ZOOM ----->
  // ---------------->

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

  // <----------------
  // <----- ZOOM -----
  // <----------------


}

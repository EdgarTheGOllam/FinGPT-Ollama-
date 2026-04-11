import sys
import webview

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    
    # Simple mapping for interval
    interval = "D"
    if len(sys.argv) > 2:
        tf = sys.argv[2]
        if "M1" in tf and "M15" not in tf: interval = "1"
        elif "M5" in tf: interval = "5"
        elif "M15" in tf: interval = "15"
        elif "M30" in tf: interval = "30"
        elif "H1" in tf: interval = "60"
        elif "H4" in tf: interval = "240"

    # Default to FX prefix, can be adjusted
    tv_symbol = f"FX:{symbol}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>body, html {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #1A1D24; }}</style>
    </head>
    <body>
    <div class="tradingview-widget-container" style="height:100%;width:100%">
      <div id="tradingview_chart" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
          new TradingView.widget({{
              "autosize": true,
              "symbol": "{tv_symbol}",
              "interval": "{interval}",
              "timezone": "Etc/UTC",
              "theme": "dark",
              "style": "1",
              "locale": "de",
              "enable_publishing": false,
              "backgroundColor": "#1A1D24",
              "gridColor": "#272B35",
              "hide_top_toolbar": false,
              "hide_legend": false,
              "save_image": false,
              "container_id": "tradingview_chart",
              "studies": [
                  "MACD@tv-basicstudies",
                  "RSI@tv-basicstudies"
              ]
          }});
      </script>
    </div>
    </body>
    </html>
    """
    
    window = webview.create_window(f"FinGPT Interactive Chart - {symbol}", html=html, width=1000, height=700, background_color='#1A1D24')
    webview.start()

if __name__ == '__main__':
    main()

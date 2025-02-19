time curl 127.0.0.1:9001/inference -H "Content-Type: multipart/form-data" -F file="@test/1.mp3" -F temperature="0.0" -F temperature_inc="0.2" -F response_format="json"

time curl 127.0.0.1:9001/inference -H "Content-Type: multipart/form-data" -F file="@./zh-cn/1L.mp3" -F temperature="0.0" -F temperature_inc="0.2" -F response_format="json" -F lang="zh-cn"

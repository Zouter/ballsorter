docker build -t zouter/framboos .
docker push zouter/framboos




####

docker run --net=host -P --name framboos zouter/framboos

docker kill framboos;docker stop framboos;docker rm framboos


# How to Add New Backend Functionality in Django

## Model Views

1. **Define URLs for the Class**: Ensure that your model is accessible via URLs by linking it to the appropriate views (`backend/backend/urls`). It maps *requests* to request handler. For example:
  ```py
    path("video/upload", views.VideoUpload.as_view(), name="video_upload"),
    path("video/list", views.VideoList.as_view(), name="video_list"),
    path("video/get", views.VideoGet.as_view(), name="video_get"),
  ```
   
2. **Create a New View**: Implement a new view that will handle requests related to your model. See examples for various GET and POST requests in `backend/backend/views/*`. For example, a class can create/update/delete DB entries or load data from backend storage.

3. **(Optional) Create a New Class in models.py**: If you need to add a new model, refer to the Django documentation on [migrations](https://docs.djangoproject.com/en/5.1/topics/migrations/).
   - Run the following command to create migrations for your changes:
     ```bash
     sudo docker-compose exec backend python3 manage.py makemigrations
     ```
   - Apply the migrations with:
     ```bash
     sudo docker-compose exec backend python3 manage.py migrate
     ```
   - Notes:
      - No container rebuild is necessary after running migrations.
      - Auto-generated updated needs to be tracked by git


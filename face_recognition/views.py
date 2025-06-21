from rest_framework import viewsets, status
from rest_framework.response import Response
import face_recognition
from .models import PersonImages
from .serializers import PersonImagesSerializer


class PersonImagesViewSet(viewsets.ModelViewSet):
    queryset = PersonImages.objects.using('face_detection').all()
    serializer_class = PersonImagesSerializer

    def calculate_accuracy(self, distance, threshold=0.6):
        # Convert face distance to a percentage accuracy
        accuracy = (1.0 - distance) * 100 if distance < threshold else 0
        return round(accuracy, 2)

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('photo')
        if not uploaded_file:
            return Response({'detail': 'No image uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        # Load the uploaded image
        uploaded_image = face_recognition.load_image_file(uploaded_file)
        uploaded_image_encoding = face_recognition.face_encodings(uploaded_image)

        if not uploaded_image_encoding:
            return Response({'detail': 'No face found in the uploaded image.'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_image_encoding = uploaded_image_encoding[0]

        matches = []
        threshold = 0.7  # You can adjust this threshold as needed

        for person_image in PersonImages.objects.using('face_detection').all():
            stored_image_path = person_image.photo.path
            stored_image = face_recognition.load_image_file(stored_image_path)
            stored_image_encoding = face_recognition.face_encodings(stored_image)

            if not stored_image_encoding:
                continue

            stored_image_encoding = stored_image_encoding[0]

            # Calculate the distance between the uploaded image and the stored image
            face_distance = face_recognition.face_distance([stored_image_encoding], uploaded_image_encoding)[0]

            if face_distance < threshold:
                accuracy = self.calculate_accuracy(face_distance, threshold)
                if accuracy > 0:
                    match_data = {
                        'person_image': person_image,
                        'accuracy': accuracy
                    }
                    matches.append(match_data)

        if matches:
            matches.sort(key=lambda x: x['accuracy'], reverse=True)  # Sort by highest accuracy first
            response_data = []
            for match in matches:
                serializer = self.get_serializer(match['person_image'])
                match_data = serializer.data
                match_data['accuracy'] = match['accuracy']
                response_data.append(match_data)
            return Response(response_data, status=status.HTTP_200_OK)

        # If no match is found, create a new PersonImages instance
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
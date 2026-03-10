# US-WEB-PROFILE-PHOTO-1

## Goal
Специалист управляет фото профиля прямо на `/profile/edit`: видит текущее фото (thumbnail), удаляет его, и безопасно заменяет новым.

## Delivered behavior
- В блоке «Фото» отображается текущая миниатюра, если фото существует.
- Добавлена явная кнопка удаления (крестик) для текущего фото.
- Добавлен `DELETE /api/specialist/profile/photo` для удаления фото.
- Upload нового фото сохраняет replace-семантику: в БД остается только одна photo-запись, старый файл очищается.
- Документы не затрагиваются операциями фото.

## Invariants
- Для профиля специалиста поддерживается не более одного `media_type=photo`.
- Удаление фото затрагивает только `media_type=photo`.
- Очистка storage выполняется после фиксации DB-изменений.

## Verification
- Backend API тесты покрывают upload/replace/delete/unauthorized/document isolation.
- `/profile/edit` содержит элементы thumbnail + delete control и JS-обработчик удаления.

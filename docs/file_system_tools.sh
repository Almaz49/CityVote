# Создать новую директорию
mkdir /path/to/new_directory

# Создать несколько вложенных директорий одновременно
mkdir -p /path/to/parent/child/grandchild

# Удалить файл
rm /path/to/file

# Удалить директорию (если она пустая)
rmdir /path/to/directory

# Удалить директорию и всё её содержимое
rm -rf /path/to/directory

# Скопировать файл
cp /path/to/source_file /path/to/destination_file

# Скопировать директорию со всем содержимым
cp -r /path/to/source_directory /path/to/destination_directory

# Переименовать файл или директорию
mv /path/to/old_name /path/to/new_name

# Найти файл по имени
find /path/to/search -name "filename"

# Найти файлы с определённым расширением
find /path/to/search -name "*.txt"

# Просмотреть содержимое файла
cat /path/to/file

# Просмотреть содержимое файла постранично
less /path/to/file

# Просмотреть права доступа к файлу или директории
ls -l /path/to/file_or_directory

# Изменить права доступа к файлу
chmod 644 /path/to/file

# Изменить владельца файла
sudo chown username:groupname /path/to/file